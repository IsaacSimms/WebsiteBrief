# == d2l.py == #
# Playwright scraper for D2L/Brightspace LMS.
#
# BEFORE YOUR FIRST REAL RUN — selector calibration:
#   1. Open your institution's D2L in Chrome
#   2. Press F12 → Elements tab
#   3. Find the course links, assignment table rows, and announcement widgets
#   4. Update the `selectors` block in config.yaml to match what you see
#   5. No Python changes needed — all selectors live in config.yaml
#
# Login flow:
#   1. Browser opens (visible, not headless) and navigates to login_url
#   2. Username is pre-filled from the D2L_USERNAME env var (if found)
#   3. A prompt appears in the terminal: complete password + MFA in the browser
#   4. Press Enter in the terminal when the D2L home page has fully loaded
#   5. OR close the browser window / let the timeout expire to cancel gracefully

from __future__ import annotations
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

from scrapers.base import BaseScraper, ScraperError, LoginCancelledError
from core.models import Assignment, WeeklyCourseData
from core.date_utils import parse_date

log = logging.getLogger(__name__)


class D2LScraper(BaseScraper):
    # == D2LScraper == #
    # requires_auth = True because a human must complete MFA in the browser.
    # run.py checks this flag before starting an unattended scheduled run.

    requires_auth: bool = True

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    # == Public interface == #

    def scrape(self) -> list[WeeklyCourseData]:
        self._start_browser()
        self._login()
        return self._scrape_all_courses()

    def close(self) -> None:
        # Close everything in reverse order. Each step is guarded so a failure
        # in one doesn't prevent the others from running.
        for obj, method in [
            (self._page,        "close"),
            (self._context,     "close"),
            (self._browser,     "close"),
            (self._playwright,  "stop"),
        ]:
            if obj is not None:
                try:
                    getattr(obj, method)()
                except Exception as exc:
                    log.debug("Ignoring error during cleanup: %s", exc)

    # == Private: browser setup == #

    def _start_browser(self) -> None:
        log.info("Launching Chromium browser (headless=False)...")
        self._playwright = sync_playwright().start()
        # headless=False is required — the user must see the browser to complete MFA.
        self._browser = self._playwright.chromium.launch(headless=False)
        self._context = self._browser.new_context()
        self._page    = self._context.new_page()

    # == Private: login == #

    def _login(self) -> None:
        login_url = self.config.get("login_url", "").strip()
        if not login_url or not login_url.startswith("http"):
            raise ScraperError(
                "config.yaml is missing a valid scrapers.d2l.login_url. "
                "It must start with http or https."
            )

        log.info("Navigating to login URL: %s", login_url)
        self._page.goto(login_url, timeout=30_000)
        self._page.wait_for_load_state("networkidle", timeout=30_000)

        # Pre-fill username if we can find the field.
        username = os.environ.get("D2L_USERNAME", "")
        if username:
            selectors_to_try = [
                'input[name="username"]',
                'input[id="username"]',
                'input[type="text"]',
                'input[autocomplete="username"]',
            ]
            for sel in selectors_to_try:
                try:
                    self._page.fill(sel, username, timeout=3_000)
                    log.debug("Pre-filled username using selector: %s", sel)
                    break
                except Exception:
                    continue
            else:
                log.warning("Could not pre-fill username — type it manually in the browser.")

        # Pause and wait for the human to complete login + MFA.
        timeout_seconds = int(self.config.get("login_timeout_seconds", 300))
        print("\n" + "=" * 60)
        print("  ACTION REQUIRED IN THE BROWSER WINDOW")
        print("  Complete your login (password + MFA).")
        print(f"  You have {timeout_seconds} seconds, or close the")
        print("  browser window at any time to cancel.")
        print("  When the D2L home page has fully loaded,")
        print("  come back here and press Enter to continue.")
        print("=" * 60 + "\n")

        result = self._wait_for_login(timeout_seconds)

        if result == "browser_closed":
            raise LoginCancelledError("Browser was closed — login cancelled.")
        if result == "timeout":
            raise LoginCancelledError(
                f"Login timed out after {timeout_seconds} seconds — login cancelled."
            )

        # Verify we are no longer on a login page.
        current_url = self._page.url
        if any(kw in current_url.lower() for kw in ("login", "signin", "auth")):
            raise ScraperError(
                "Login may not have succeeded — the browser is still on a login-like URL. "
                f"Current URL: {current_url}"
            )

        log.info("Login confirmed. Current URL: %s", current_url)

    def _wait_for_login(self, timeout_seconds: int) -> str:
        # == _wait_for_login == #
        # Wait for one of three things, whichever comes first:
        #   "confirmed"      — user pressed Enter in the terminal
        #   "browser_closed" — user closed the browser window
        #   "timeout"        — timeout_seconds elapsed
        #
        # Uses a daemon thread so input() blocking doesn't freeze the main thread.
        # The main thread polls browser connectivity and the countdown every second.

        event = threading.Event()
        result_holder: list[str] = []

        def wait_for_enter() -> None:
            try:
                input()             # blocks until user presses Enter
                result_holder.append("confirmed")
            except (EOFError, OSError):
                # stdin closed (e.g. scheduled run with no terminal attached)
                result_holder.append("stdin_closed")
            finally:
                event.set()

        thread = threading.Thread(target=wait_for_enter, daemon=True)
        thread.start()

        elapsed = 0
        while elapsed < timeout_seconds:
            if event.is_set():
                return result_holder[0] if result_holder else "confirmed"
            if self._browser and not self._browser.is_connected():
                return "browser_closed"
            time.sleep(1)
            elapsed += 1

        return "timeout"

    # == Private: scraping == #

    def _scrape_all_courses(self) -> list[WeeklyCourseData]:
        selectors = self.config.get("selectors", {})
        course_link_selector = selectors.get("course_links", 'a[href*="/d2l/home/"]')

        # Try to navigate to the home page before looking for course links.
        base_url = self._extract_base_url(self._page.url)
        try:
            self._page.goto(f"{base_url}/d2l/home", timeout=20_000)
            self._page.wait_for_load_state("networkidle", timeout=20_000)
        except Exception as exc:
            log.warning("Could not navigate to /d2l/home — trying current page. (%s)", exc)

        # Extract course links from the page.
        try:
            # wait_for_selector ensures the JS has rendered before we query.
            self._page.wait_for_selector(course_link_selector, timeout=15_000)
            course_links: list[dict] = self._page.eval_on_selector_all(
                course_link_selector,
                "els => els.map(el => ({ href: el.href, text: el.innerText.trim() }))",
            )
        except Exception as exc:
            raise ScraperError(
                f"Could not find course links using selector '{course_link_selector}'. "
                f"Open config.yaml and update scrapers.d2l.selectors.course_links "
                f"to match your institution's D2L. ({exc})"
            )

        if not course_links:
            log.warning(
                "No course links found with selector '%s'. "
                "The selector may need updating for your institution.",
                course_link_selector,
            )
            return []

        results: list[WeeklyCourseData] = []
        seen_urls: set[str] = set()

        log.info("Found %d potential course link(s). Filtering and scraping...", len(course_links))

        for link in course_links:
            url  = link.get("href", "")
            name = link.get("text", "").strip()

            # Skip empty names, very short strings (likely nav links), and duplicates.
            if not name or len(name) < 4 or url in seen_urls:
                continue
            seen_urls.add(url)

            log.info("  Scraping course: %s", name)
            try:
                course_data = self._scrape_one_course(url, name)
                results.append(course_data)
            except LoginCancelledError:
                raise    # propagate cancel signals immediately
            except Exception as exc:
                # Log the failure but continue with the remaining courses.
                log.warning("  Could not scrape '%s': %s", name, exc)

        log.info("Scraping complete. %d course(s) collected.", len(results))
        return results

    def _scrape_one_course(self, course_url: str, course_name: str) -> WeeklyCourseData:
        self._page.goto(course_url, timeout=20_000)
        self._page.wait_for_load_state("networkidle", timeout=20_000)
        scraped_at = datetime.now(timezone.utc)

        assignments  = self._scrape_assignments(course_url)
        announcements = self._scrape_announcements()

        return WeeklyCourseData(
            course_name=course_name,
            scraped_at=scraped_at,
            assignments=assignments,
            announcements=announcements,
            scraper_name="d2l",
        )

    def _scrape_assignments(self, course_url: str) -> list[Assignment]:
        selectors = self.config.get("selectors", {})
        row_sel   = selectors.get("assignment_rows", "table tr")
        title_col = int(selectors.get("assignment_title_cell", 0))
        due_col   = int(selectors.get("assignment_due_cell",   1))
        status_col = int(selectors.get("assignment_status_cell", 2))

        # Navigate to the assignments/dropbox page for this course.
        org_unit_id = self._extract_org_unit_id(course_url)
        if not org_unit_id:
            log.debug("Could not extract org unit ID from %s", course_url)
            return []

        base_url       = self._extract_base_url(self._page.url)
        assignments_url = f"{base_url}/d2l/lms/dropbox/user/folders_list.d2l?ou={org_unit_id}"

        try:
            self._page.goto(assignments_url, timeout=15_000)
            self._page.wait_for_load_state("networkidle", timeout=15_000)
            # Wait for at least one row, but don't fail if none appear.
            self._page.wait_for_selector(row_sel, timeout=8_000)
        except Exception as exc:
            log.debug("Assignments page unavailable or empty: %s", exc)
            return []

        try:
            rows: list[dict | None] = self._page.eval_on_selector_all(
                row_sel,
                f"""rows => rows.map(row => {{
                    const cells = Array.from(row.querySelectorAll("td, th"));
                    if (cells.length < 2) return null;
                    return {{
                        title:  (cells[{title_col}]  || {{}}).innerText?.trim() || "",
                        due:    (cells[{due_col}]    || {{}}).innerText?.trim() || "",
                        status: (cells[{status_col}] || {{}}).innerText?.trim() || ""
                    }};
                }}).filter(r => r && r.title && r.title.length > 1)""",
            )
        except Exception as exc:
            log.warning("Could not read assignment rows: %s", exc)
            return []

        assignments: list[Assignment] = []
        for row in rows:
            if not row:
                continue
            assignments.append(Assignment(
                title=row["title"],
                due_date=parse_date(row.get("due", "")),
                status=row.get("status") or None,
            ))

        log.debug("  Found %d assignment(s) in dropbox.", len(assignments))
        return assignments

    def _scrape_announcements(self) -> list[str]:
        selectors        = self.config.get("selectors", {})
        announce_sel     = selectors.get(
            "announcement_widget",
            '[class*="news"], [class*="announcement"]',
        )
        try:
            texts: list[str] = self._page.eval_on_selector_all(
                announce_sel,
                "els => els.map(el => el.innerText.trim()).filter(t => t.length > 10)",
            )
            # Truncate very long announcements to avoid bloating the prompt.
            trimmed = [t[:400] + "..." if len(t) > 400 else t for t in texts]
            return trimmed[:5]    # at most 5 announcements per course
        except Exception as exc:
            log.debug("Could not read announcements: %s", exc)
            return []

    # == Private: URL helpers == #

    @staticmethod
    def _extract_base_url(url: str) -> str:
        # "https://learn.myuni.edu/d2l/home/12345" → "https://learn.myuni.edu"
        match = re.match(r"(https?://[^/]+)", url)
        return match.group(1) if match else url

    @staticmethod
    def _extract_org_unit_id(url: str) -> str | None:
        # "/d2l/home/12345" → "12345"
        match = re.search(r"/d2l/home/(\d+)", url)
        return match.group(1) if match else None
