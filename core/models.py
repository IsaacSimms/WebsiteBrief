# == models.py == #
# Shared data structures for the WebsiteBrief pipeline.
#
# Every scraper — D2L, GitHub, news sites, anything — must produce
# ScrapeResult objects. The rest of the pipeline (AI client, storage)
# only knows about this schema, so it never changes when a new scraper
# is added.
#
# These are plain dataclasses: data containers with no logic.
# Think of them like structs in other languages.

from __future__ import annotations                    # allows list[X] syntax on older Python
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DataItem:
    # == DataItem == #
    # Represents one scraped entry from a source page.
    # Could be an assignment, a repo, an article, a job listing — anything.
    # Only `title` is required; everything else may be absent from the page.

    title: str                                        # e.g. "Homework 3", "torvalds/linux"
    event_date: datetime | None = None                # UTC-aware; None if not applicable
    status: str | None = None                         # e.g. "Not Started", "Open", "Closed"
    description: str | None = None                    # scraped detail text, if any
    url: str | None = None                            # direct link to the item

    # metadata holds any domain-specific numeric or string values that don't fit
    # the other fields. Examples:
    #   D2L assignment: {"points": 100}
    #   GitHub repo:    {"stars": 4200, "language": "Python"}
    #   News article:   {"word_count": 850, "author": "Jane Smith"}
    # Defaults to an empty dict — callers that don't need it pay no cost.
    metadata: dict = field(default_factory=dict)


@dataclass
class ScrapeResult:
    # == ScrapeResult == #
    # The standard output contract every scraper must fulfill.
    # Changing the scraper never requires changing the AI client or storage
    # because they only ever see this type.

    source_name: str                                  # human-readable name of the scraped source
    scraped_at: datetime                              # UTC-aware timestamp of the scrape

    # field(default_factory=list) is required for mutable defaults in dataclasses.
    # Writing `= []` here would cause all instances to share one list — a Python gotcha.
    results: list[DataItem] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)   # key items or notices from the page

    raw_notes: str = ""                               # freeform pass-through text
    scraper_name: str = ""                            # e.g. "d2l", "github_trending"
