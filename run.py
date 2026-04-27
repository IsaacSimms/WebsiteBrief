# == run.py == #
# Main entry point for the WebsiteBrief pipeline.
#
# Usage (with .venv active):
#   python run.py                  — full interactive run
#   python run.py --dry-run        — scrape only; print prompt, skip AI + file saves
#   python run.py --unattended     — skip scrapers that require human login
#   python run.py --scraper d2l    — override the active scraper in config.yaml
#   python run.py --verbose        — DEBUG log level
#   python run.py --no-save        — don't write any output files (useful for testing)
#   python run.py --no-cleanup     — skip old-file deletion this run
#   python run.py --help           — show all options

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

# == Load .env before anything else == #
# python-dotenv reads .env and sets each KEY=VALUE as an environment variable.
# This must happen before importing any module that reads os.environ (e.g. ClaudeClient).
from dotenv import load_dotenv
load_dotenv()

import yaml

log = logging.getLogger(__name__)


# == Logging Setup == #

def setup_logging(verbose: bool = False) -> None:
    # Create the logs directory now — before the first log line is written.
    Path("outputs/logs").mkdir(parents=True, exist_ok=True)

    level = logging.DEBUG if verbose else logging.INFO
    fmt   = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)    # root always captures DEBUG; handlers filter

    # Console: INFO by default, DEBUG with --verbose.
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter(fmt))
    root.addHandler(console)

    # Rotating file: always DEBUG, max 5 MB per file, keep 3 backups.
    # After 3 rotations the oldest file is deleted automatically.
    file_handler = RotatingFileHandler(
        "outputs/logs/websitebrief.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(fmt))
    root.addHandler(file_handler)


# == CLI Arguments == #

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python run.py",
        description="WebsiteBrief — scrape web data and generate a weekly AI brief.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape data and print the prompt, but skip the AI call and file saves.",
    )
    parser.add_argument(
        "--unattended",
        action="store_true",
        help="Exit cleanly if the active scraper requires human interaction (requires_auth=True).",
    )
    parser.add_argument(
        "--scraper",
        metavar="NAME",
        help="Override the active scraper from config.yaml (e.g. --scraper d2l).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG log level for detailed output.",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't write any output files (brief or conversation log).",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Skip deletion of old brief files this run.",
    )
    return parser.parse_args()


# == Config Loading == #

def load_config() -> dict:
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        if not isinstance(cfg, dict):
            raise ValueError("config.yaml did not parse to a dictionary.")
        return cfg
    except FileNotFoundError:
        print("ERROR: config.yaml not found. Run from the project root directory.")
        sys.exit(1)
    except (yaml.YAMLError, ValueError) as exc:
        print(f"ERROR: config.yaml has a syntax error: {exc}")
        sys.exit(1)


# == Config Validation == #

def validate_config(cfg: dict, active_scraper: str) -> None:
    # == validate_config == #
    # Checks required config keys and environment variables BEFORE any browser
    # or API calls. Prints a clear, specific error for every problem found,
    # then exits with code 1 if anything is wrong.
    # "Fail fast with a useful message" is the goal.

    errors: list[str] = []

    # -- Scraper block --
    scrapers_cfg = cfg.get("scrapers", {})
    if not scrapers_cfg.get("active") and not active_scraper:
        errors.append("scrapers.active is missing from config.yaml.")
    if active_scraper not in scrapers_cfg and active_scraper:
        errors.append(
            f"No config block found for scraper '{active_scraper}' in config.yaml. "
            f"Add a 'scrapers.{active_scraper}:' block."
        )

    # D2L-specific checks
    if active_scraper == "d2l":
        d2l_cfg  = scrapers_cfg.get("d2l", {})
        login_url = d2l_cfg.get("login_url", "").strip()
        if not login_url:
            errors.append("scrapers.d2l.login_url is missing from config.yaml.")
        elif not login_url.startswith("http"):
            errors.append(
                f"scrapers.d2l.login_url does not look like a URL: '{login_url}'. "
                "It must start with http or https."
            )
        if not os.environ.get("D2L_USERNAME"):
            errors.append(
                "D2L_USERNAME is not set in your .env file. "
                "Add:  D2L_USERNAME=your_username"
            )

    # -- LLM block --
    llm_cfg  = cfg.get("llm", {})
    provider = llm_cfg.get("provider", "").strip()
    if not provider:
        errors.append("llm.provider is missing from config.yaml.")
    else:
        providers = llm_cfg.get("providers", {})
        if provider not in providers:
            errors.append(
                f"No config block for LLM provider '{provider}' in config.yaml. "
                f"Add a 'llm.providers.{provider}:' block."
            )

    # -- Anthropic API key --
    if not os.environ.get("ANTHROPIC_API_KEY"):
        errors.append(
            "ANTHROPIC_API_KEY is not set in your .env file. "
            "Add:  ANTHROPIC_API_KEY=sk-ant-..."
        )

    if errors:
        print("\nConfiguration errors found — fix these before running:\n")
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}")
        print()
        sys.exit(1)


# == Factory Functions == #

def build_scraper(cfg: dict, active: str):
    # == build_scraper == #
    # Returns a BaseScraper instance for the configured scraper.
    # TO ADD A NEW SCRAPER: add an elif branch here, that is all.

    scraper_cfg = cfg["scrapers"].get(active, {})

    if active == "d2l":
        from scrapers.d2l import D2LScraper
        return D2LScraper(scraper_cfg)

    # elif active == "canvas":
    #     from scrapers.canvas import CanvasScraper
    #     return CanvasScraper(scraper_cfg)

    print(f"ERROR: Unknown scraper '{active}'. Add it to run.py's build_scraper().")
    sys.exit(1)


def build_llm_client(cfg: dict):
    # == build_llm_client == #
    # Returns a BaseLLMClient instance for the configured provider.
    # TO ADD A NEW PROVIDER: add an elif branch here, that is all.

    provider     = cfg["llm"]["provider"]
    provider_cfg = cfg["llm"]["providers"][provider]

    if provider == "claude":
        from core.claude_client import ClaudeClient
        return ClaudeClient(provider_cfg)

    # elif provider == "openai":
    #     from core.openai_client import OpenAIClient
    #     return OpenAIClient(provider_cfg)

    print(f"ERROR: Unknown LLM provider '{provider}'. Add it to run.py's build_llm_client().")
    sys.exit(1)


# == Prompt Formatting == #

def format_prompt(sources: list, cfg: dict) -> str:
    # == format_prompt == #
    # Converts ScrapeResult objects into a plain-text prompt for the AI.
    # Applies the 7-day filter here — the AI only sees items within the next week.
    # Items with no event_date are always included (can't filter what we don't know).

    from core.date_utils import is_within_days

    lines = [
        "Generate a weekly brief for the following scraped data.",
        f"Data collected at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]

    for source in sources:
        lines.append(f"SOURCE: {source.source_name}")
        lines.append(f"Scraper: {source.scraper_name}")

        # Filter to the 7-day window; keep items with no event_date.
        upcoming = [
            item for item in source.results
            if is_within_days(item.event_date, days=7) or item.event_date is None
        ]

        if upcoming:
            lines.append(f"Items ({len(upcoming)} within 7 days or no date):")
            for item in upcoming:
                date_str   = item.event_date.strftime("%Y-%m-%d %H:%M UTC") if item.event_date else "No date"
                status_str = f" [{item.status}]" if item.status else ""
                meta_str   = (" [" + ", ".join(f"{k}: {v}" for k, v in item.metadata.items()) + "]") if item.metadata else ""
                lines.append(f"  - {item.title}{status_str}{meta_str} — Date: {date_str}")
        else:
            lines.append("Items: None in the next 7 days.")

        if source.highlights:
            lines.append("Highlights:")
            for h in source.highlights:
                lines.append(f"  - {h}")

        if source.raw_notes:
            lines.append(f"Notes: {source.raw_notes}")

        lines.append("")    # blank line between sources

    return "\n".join(lines)


# == Main Pipeline == #

def main() -> None:
    args = parse_args()
    setup_logging(verbose=args.verbose)

    log.info("=" * 50)
    log.info("WebsiteBrief pipeline starting")
    log.info("=" * 50)

    cfg = load_config()

    # --scraper flag overrides config.yaml
    active_scraper = args.scraper or cfg.get("scrapers", {}).get("active", "")
    if not active_scraper:
        log.error("No scraper specified. Set scrapers.active in config.yaml or use --scraper.")
        sys.exit(1)

    validate_config(cfg, active_scraper)

    # -- Step 1: Scrape -- #
    log.info("[Step 1] Building scraper: %s", active_scraper)
    scraper = build_scraper(cfg, active_scraper)

    # Unattended mode: skip scrapers that require a human to be present.
    if args.unattended and scraper.requires_auth:
        log.warning(
            "Scraper '%s' requires human authentication (requires_auth=True). "
            "Exiting cleanly because --unattended flag is set.",
            active_scraper,
        )
        sys.exit(0)

    from scrapers.base import LoginCancelledError, ScraperError
    from core.base_llm_client import LLMError

    try:
        with scraper:
            sources = scraper.scrape()
    except LoginCancelledError as exc:
        log.warning("Login cancelled: %s", exc)
        print("\nRun cancelled — no brief was generated.")
        sys.exit(0)
    except ScraperError as exc:
        log.error("Scraper failed: %s", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        log.info("Interrupted by user.")
        sys.exit(0)

    if not sources:
        log.warning("Scraper returned no data. Nothing to brief.")
        sys.exit(0)

    log.info("[Step 2] Scraped %d source(s). Building prompt...", len(sources))
    prompt = format_prompt(sources, cfg)

    # -- Dry run stops here -- #
    if args.dry_run:
        print("\n" + "=" * 50)
        print("DRY RUN — prompt that would be sent to the AI:")
        print("=" * 50)
        print(prompt)
        print("=" * 50)
        print("(AI was not called. No files were written.)")
        sys.exit(0)

    # -- Step 2: Generate brief -- #
    log.info("[Step 3] Generating brief with AI...")
    try:
        llm    = build_llm_client(cfg)
        brief  = llm.generate_brief(prompt)
    except LLMError as exc:
        log.error("AI brief generation failed: %s", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        log.info("Interrupted by user during AI call.")
        sys.exit(0)

    # -- Step 3: Save outputs -- #
    if not args.no_save:
        log.info("[Step 4] Saving outputs...")
        from core.storage import save_brief, save_conversation
        output_cfg        = cfg.get("output", {})
        retention_days    = int(output_cfg.get("brief_retention_days", 30))
        save_conversations = output_cfg.get("save_conversations", True)

        cleanup = not args.no_cleanup
        save_brief(brief, retention_days=retention_days if cleanup else 99999)

        if save_conversations:
            save_conversation(prompt, brief)
    else:
        log.info("--no-save set: skipping file writes.")

    log.info("=" * 50)
    log.info("Done. Check outputs/briefs/ for your brief.")
    log.info("=" * 50)


if __name__ == "__main__":
    main()
