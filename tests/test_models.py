# == test_models.py == #
# Tests for core/models.py.
# Run with:  pytest tests/test_models.py -v

import pytest
from datetime import datetime, timezone
from core.models import DataItem, ScrapeResult


# == DataItem Tests == #

class TestDataItem:

    def test_requires_only_title(self):
        # All fields except title are optional.
        item = DataItem(title="Homework 1")
        assert item.title == "Homework 1"
        assert item.event_date is None
        assert item.status is None
        assert item.description is None
        assert item.url is None
        assert item.metadata == {}        # empty dict, not None

    def test_accepts_all_fields(self):
        due = datetime(2026, 4, 30, 23, 59, tzinfo=timezone.utc)
        item = DataItem(
            title="Final Project",
            event_date=due,
            status="Not Started",
            description="Write a 10-page report",
            url="https://example.com/assignments/1",
            metadata={"points": 100, "weight": "30%"},
        )
        assert item.event_date == due
        assert item.status == "Not Started"
        assert item.metadata["points"] == 100

    def test_metadata_defaults_to_empty_dict(self):
        item = DataItem(title="Repo")
        assert item.metadata == {}
        assert isinstance(item.metadata, dict)

    def test_metadata_accepts_mixed_values(self):
        # metadata can hold any key-value pairs — strings, ints, floats.
        item = DataItem(
            title="torvalds/linux",
            metadata={"stars": 182_000, "language": "C", "forks": 53_000},
        )
        assert item.metadata["stars"] == 182_000
        assert item.metadata["language"] == "C"

    def test_two_instances_are_independent(self):
        i1 = DataItem(title="A")
        i2 = DataItem(title="B")
        assert i1 is not i2
        assert i1.title != i2.title

    def test_two_instances_do_not_share_metadata_dict(self):
        # field(default_factory=dict) prevents instances from sharing one dict.
        i1 = DataItem(title="A")
        i2 = DataItem(title="B")
        i1.metadata["key"] = "value"
        assert "key" not in i2.metadata, "Modifying i1.metadata must not affect i2"


# == ScrapeResult Tests == #

class TestScrapeResult:

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def test_requires_source_name_and_scraped_at(self):
        now = self._now()
        sr = ScrapeResult(source_name="COMP 101", scraped_at=now)
        assert sr.source_name == "COMP 101"
        assert sr.scraped_at == now

    def test_results_default_to_empty_list(self):
        sr = ScrapeResult(source_name="X", scraped_at=self._now())
        assert sr.results == []

    def test_highlights_default_to_empty_list(self):
        sr = ScrapeResult(source_name="X", scraped_at=self._now())
        assert sr.highlights == []

    def test_raw_notes_defaults_to_empty_string(self):
        sr = ScrapeResult(source_name="X", scraped_at=self._now())
        assert sr.raw_notes == ""

    def test_scraper_name_defaults_to_empty_string(self):
        sr = ScrapeResult(source_name="X", scraped_at=self._now())
        assert sr.scraper_name == ""

    def test_two_instances_do_not_share_results_list(self):
        # This catches the classic Python mutable-default-argument bug.
        # field(default_factory=list) prevents both instances from pointing
        # at the same list object.
        now = self._now()
        s1 = ScrapeResult(source_name="S1", scraped_at=now)
        s2 = ScrapeResult(source_name="S2", scraped_at=now)
        s1.results.append(DataItem(title="Item1"))
        assert len(s2.results) == 0, "Modifying s1.results must not affect s2"

    def test_two_instances_do_not_share_highlights_list(self):
        now = self._now()
        s1 = ScrapeResult(source_name="S1", scraped_at=now)
        s2 = ScrapeResult(source_name="S2", scraped_at=now)
        s1.highlights.append("Important notice")
        assert len(s2.highlights) == 0

    def test_can_add_results(self):
        sr = ScrapeResult(source_name="GitHub Trending", scraped_at=self._now())
        sr.results.append(DataItem(title="torvalds/linux", metadata={"stars": 182_000}))
        assert len(sr.results) == 1
        assert sr.results[0].title == "torvalds/linux"

    def test_scraped_at_is_timezone_aware(self):
        # All datetimes in this project must carry timezone info.
        # A naive datetime (no tzinfo) is treated as a bug.
        now = datetime.now(timezone.utc)
        sr = ScrapeResult(source_name="X", scraped_at=now)
        assert sr.scraped_at.tzinfo is not None
