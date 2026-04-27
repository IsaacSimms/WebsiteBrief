# == base.py == #
# Abstract base class for all website scrapers.
#
# ADDING A NEW SCRAPER — checklist:
#   1. Create scrapers/<name>.py
#   2. Subclass BaseScraper
#   3. Implement scrape() and close()
#   4. Set requires_auth = True if a human must be present for login
#   5. Add a config block in config.yaml under scrapers.<name>
#   6. Add one elif branch in run.py's _build_scraper()
#   That is all. Nothing else in the pipeline changes.

from __future__ import annotations
from abc import ABC, abstractmethod
from core.models import ScrapeResult


class BaseScraper(ABC):
    # == BaseScraper == #
    # Every scraper must inherit this class and implement all abstract methods.
    # Python will raise TypeError at import time if any are missing — fast feedback.

    # Set to True in scrapers that open a browser and wait for human login.
    # run.py checks this before starting an unattended scheduled run.
    requires_auth: bool = False

    def __init__(self, config: dict) -> None:
        # config is the dict from config.yaml for this specific scraper.
        # e.g. for D2L it is config["scrapers"]["d2l"]
        self.config = config

    @abstractmethod
    def scrape(self) -> list[ScrapeResult]:
        # Run the full scrape and return one ScrapeResult per source found.
        # Must return an empty list (not raise) when nothing is found.
        ...

    @abstractmethod
    def close(self) -> None:
        # Release all resources: close browser, end sessions, etc.
        # Always called by the context manager, even if scrape() raised.
        ...

    def __enter__(self) -> BaseScraper:
        # Enables:  with D2LScraper(cfg) as scraper:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.close()
        return False    # False = do not suppress exceptions; let them propagate


class ScraperError(Exception):
    # == ScraperError == #
    # Raised for non-recoverable scraper failures: network down, page layout
    # changed, selector returned nothing, etc.
    # run.py catches this and exits with code 1 (failure).
    pass


class LoginCancelledError(ScraperError):
    # == LoginCancelledError == #
    # Raised when the user closes the browser window or the login timeout elapses.
    # This is NOT a failure — the user chose to stop.
    # run.py catches this separately and exits with code 0 (success/clean stop).
    pass
