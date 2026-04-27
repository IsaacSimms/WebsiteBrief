# == test_base.py == #
# Tests for scrapers/base.py and core/base_llm_client.py.
# Written BEFORE the implementation — this is TDD.
# Run with:  pytest tests/test_base.py -v

import pytest
from datetime import datetime, timezone
from core.models import ScrapeResult
from scrapers.base import BaseScraper, ScraperError, LoginCancelledError
from core.base_llm_client import BaseLLMClient, LLMError


# == BaseScraper Tests == #

class TestBaseScraper:

    def test_cannot_instantiate_abstract_class_directly(self):
        # Python refuses to create an instance of an abstract class.
        # This guarantees you cannot accidentally use BaseScraper without
        # implementing its required methods.
        with pytest.raises(TypeError):
            BaseScraper(config={})

    def test_subclass_missing_scrape_cannot_be_instantiated(self):
        class MissingScrape(BaseScraper):
            def close(self) -> None:
                pass
            # scrape() is intentionally missing

        with pytest.raises(TypeError):
            MissingScrape(config={})

    def test_subclass_missing_close_cannot_be_instantiated(self):
        class MissingClose(BaseScraper):
            def scrape(self) -> list[ScrapeResult]:
                return []
            # close() is intentionally missing

        with pytest.raises(TypeError):
            MissingClose(config={})

    def test_complete_subclass_can_be_instantiated(self):
        class GoodScraper(BaseScraper):
            def scrape(self) -> list[ScrapeResult]:
                return []
            def close(self) -> None:
                pass

        scraper = GoodScraper(config={"key": "value"})
        assert scraper.config == {"key": "value"}
        assert scraper.scrape() == []

    def test_requires_auth_defaults_to_false(self):
        # Scrapers that don't need a human present leave this as False.
        class NoAuthScraper(BaseScraper):
            def scrape(self): return []
            def close(self): pass

        assert NoAuthScraper.requires_auth is False

    def test_requires_auth_can_be_set_true(self):
        class AuthScraper(BaseScraper):
            requires_auth = True
            def scrape(self): return []
            def close(self): pass

        assert AuthScraper.requires_auth is True

    def test_context_manager_calls_close_on_normal_exit(self):
        # __exit__ must call close() even when scrape() succeeds.
        close_calls = []

        class FakeScraper(BaseScraper):
            def scrape(self): return []
            def close(self): close_calls.append(1)

        with FakeScraper(config={}) as s:
            s.scrape()

        assert close_calls == [1], "close() must be called exactly once on exit"

    def test_context_manager_calls_close_on_exception(self):
        # __exit__ must call close() even when an exception is raised inside the block.
        close_calls = []

        class FakeScraper(BaseScraper):
            def scrape(self): raise ScraperError("boom")
            def close(self): close_calls.append(1)

        with pytest.raises(ScraperError):
            with FakeScraper(config={}) as s:
                s.scrape()

        assert close_calls == [1], "close() must be called even when an exception occurs"

    def test_context_manager_does_not_suppress_exceptions(self):
        # __exit__ returns False, so exceptions propagate to the caller.
        class FakeScraper(BaseScraper):
            def scrape(self): raise ScraperError("propagate me")
            def close(self): pass

        with pytest.raises(ScraperError, match="propagate me"):
            with FakeScraper(config={}) as s:
                s.scrape()


# == ScraperError / LoginCancelledError Tests == #

class TestScraperErrors:

    def test_scraper_error_is_an_exception(self):
        with pytest.raises(ScraperError, match="network timeout"):
            raise ScraperError("network timeout")

    def test_login_cancelled_is_a_scraper_error(self):
        # LoginCancelledError must be catchable as a ScraperError too.
        with pytest.raises(ScraperError):
            raise LoginCancelledError("browser closed")

    def test_login_cancelled_is_its_own_type(self):
        with pytest.raises(LoginCancelledError, match="browser closed"):
            raise LoginCancelledError("browser closed")

    def test_can_distinguish_login_cancelled_from_scraper_error(self):
        # run.py needs to catch these separately — LoginCancelled is exit 0,
        # ScraperError is exit 1.
        errors_caught = []
        for exc in [ScraperError("real error"), LoginCancelledError("user quit")]:
            if isinstance(exc, LoginCancelledError):
                errors_caught.append("cancelled")
            elif isinstance(exc, ScraperError):
                errors_caught.append("error")

        assert errors_caught == ["error", "cancelled"]


# == BaseLLMClient Tests == #

class TestBaseLLMClient:

    def test_cannot_instantiate_abstract_class_directly(self):
        with pytest.raises(TypeError):
            BaseLLMClient(config={})

    def test_subclass_missing_generate_brief_cannot_be_instantiated(self):
        class IncompleteClient(BaseLLMClient):
            pass  # generate_brief() not implemented

        with pytest.raises(TypeError):
            IncompleteClient(config={})

    def test_complete_subclass_works(self):
        class EchoClient(BaseLLMClient):
            def generate_brief(self, prompt: str) -> str:
                return f"BRIEF: {prompt[:20]}"

        client = EchoClient(config={"model": "test-model"})
        result = client.generate_brief("Hello, this is a test prompt")
        assert result.startswith("BRIEF:")
        assert client.config["model"] == "test-model"

    def test_llm_error_is_an_exception(self):
        with pytest.raises(LLMError, match="API call failed"):
            raise LLMError("API call failed")
