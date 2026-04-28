# WebsiteBrief

An extensible pipeline for scraping structured data from any website and generating an AI-powered Markdown brief via the Claude API. Point it at a website, define what to collect, and get a concise summary delivered to `outputs/briefs/`. Designed to run on demand or on a schedule.

The included D2L scraper (for Brightspace LMS) is the reference implementation — it shows exactly what building a scraper looks like.

---

## Architecture

```
run.py
  ├─ BaseScraper (scrapers/base.py)      ←  implement this for any website
  │   └─ D2LScraper (scrapers/d2l.py)   ←  reference implementation (LMS)
  │
  ├─ 7-day filter (core/date_utils.py)  ←  optional: strips items outside window
  │
  ├─ BaseLLMClient (core/base_llm_client.py)
  │   └─ ClaudeClient (core/claude_client.py)  ←  generates the brief
  │
  └─ storage (core/storage.py)           ←  saves brief + conversation log
```

Every scraper returns the same `ScrapeResult` / `DataItem` schema. The AI client and storage layer only know about that schema — swapping scrapers or AI providers never touches pipeline logic.

---

## Prerequisites

- Python 3.10 or newer ([python.org](https://www.python.org/downloads/))
- Git
- An [Anthropic API key](https://console.anthropic.com/)

---

## Setup (Windows)

**1. Clone the repo and open a terminal in the project folder.**

**2. Run the one-time setup script:**

```cmd
.\setup.bat
```

This script:
- Creates a `.venv` virtual environment
- Installs all Python dependencies (see `requirements.txt`)
- Downloads the Playwright Chromium browser
- Creates `outputs/` directories
- Copies `.env.example` → `.env`

**3. Fill in your secrets:**

Open `.env` and add your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

If you are using the D2L scraper, also add:

```
D2L_USERNAME=your_username_here
```

**4. Configure your scraper in `config.yaml`:**

Set `scrapers.active` to the scraper you want to use and fill in its block. See the per-scraper sections below.

**5. Activate the virtual environment** (required every time you open a new terminal):

```cmd
.venv\Scripts\activate.bat
```

**6. Run:**

```cmd
python run.py
```

Output appears in `outputs/briefs/`.

---

## Using the D2L Scraper

The D2L scraper automates login to a Brightspace LMS, collects your course list, upcoming assignments, and announcements, then passes them to the AI.

**`config.yaml` block:**

```yaml
scrapers:
  active: d2l
  d2l:
    login_url: "https://learn.myuniversity.edu/d2l/login"
```

Replace the URL with your institution's Brightspace login page.

When you run, a browser window opens. Complete your login (and MFA if required), then press Enter in the terminal. The scraper takes over from there.

### Calibrating CSS Selectors

Brightspace themes vary by institution, so the default selectors in `config.yaml` may not match yours. To fix:

1. Open your D2L in Chrome and log in.
2. Press **F12** → **Elements** tab.
3. Find the element you need (course links, assignment rows, announcements).
4. Right-click → **Copy** → **Copy selector**.
5. Paste it into the matching key under `scrapers.d2l.selectors` in `config.yaml`.

No Python changes needed — all selectors live in `config.yaml`.

---

## Adding a Scraper for a New Website

Three files to touch, no changes to anything else.

**1. Create `scrapers/<name>.py`:**

```python
from datetime import datetime, timezone
from scrapers.base import BaseScraper
from core.models import ScrapeResult, DataItem

class GitHubTrendingScraper(BaseScraper):
    requires_auth = False   # set True if a human must log in

    def scrape(self) -> list[ScrapeResult]:
        url = self.config.get("url", "https://github.com/trending")
        # use self.config values; use Playwright or requests to fetch the page
        items = [
            DataItem(title="example/repo", metadata={"stars": 1200}),
        ]
        return [ScrapeResult(
            source_name="GitHub Trending",
            scraper_name="github_trending",
            scraped_at=datetime.now(timezone.utc),
            results=items,
        )]

    def close(self) -> None:
        pass   # release browser or session here if you opened one
```

**`DataItem` fields** (all optional except `title`):

| Field | Type | Use for |
|---|---|---|
| `title` | `str` | Name of the item (required) |
| `event_date` | `datetime \| None` | Due dates, publish dates — UTC-aware |
| `status` | `str \| None` | "Open", "Closed", "Not Started", etc. |
| `description` | `str \| None` | Detail text scraped from the page |
| `url` | `str \| None` | Direct link to the item |
| `metadata` | `dict` | Any domain-specific values (stars, points, author…) |

**2. Add a block in `config.yaml`:**

```yaml
scrapers:
  active: github_trending
  github_trending:
    url: "https://github.com/trending"
    language: python
```

All values under `github_trending:` are available in your scraper as `self.config`.

**3. Register it in `run.py`'s `build_scraper()`:**

```python
elif active == "github_trending":
    from scrapers.github_trending import GitHubTrendingScraper
    return GitHubTrendingScraper(scraper_cfg)
```

That is all. The AI client, storage, and logging require zero changes.

**Test your scraper without spending API credits:**

```powershell
python run.py --scraper github_trending --dry-run
```

`--dry-run` prints the prompt that would be sent to Claude without calling the API.

---

## Adding a New AI Provider

1. Create `core/<provider>_client.py` and subclass `BaseLLMClient`.
2. Add a `providers.<provider>:` block to `config.yaml` and set `llm.provider`.
3. Add one `elif` branch in `run.py`'s `build_llm_client()`.
4. Add your API key to `.env`.

---

## CLI Reference

| Flag | Description |
|---|---|
| *(no flags)* | Full interactive run |
| `--dry-run` | Scrape only; print the AI prompt without calling the API |
| `--unattended` | Exit cleanly if the scraper requires human login (for scheduled runs) |
| `--scraper NAME` | Override the active scraper in config.yaml |
| `--verbose` | Enable DEBUG log level |
| `--no-save` | Skip writing output files (useful for testing) |
| `--no-cleanup` | Skip deletion of old brief files this run |
| `--help` | Show all options |

---

## Output Files

| Location | Contents |
|---|---|
| `outputs/briefs/brief_YYYYMMDD_HHMMSS.md` | Generated brief |
| `outputs/conversations/conversation_*.json` | Full prompt + response (for debugging) |
| `outputs/logs/websitebrief.log` | Rotating log file (DEBUG level, 5 MB max) |

Brief files older than `brief_retention_days` (default: 30 days) are deleted automatically on each run.

---

## Running Tests

```powershell
pytest tests/ -v
```

Tests cover: data models, abstract base classes, date parsing, storage I/O, and cleanup logic.
