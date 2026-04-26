# == models.py == #
# Shared data structures for the WebsiteBrief pipeline.
#
# Every scraper — D2L, Canvas, GitHub, anything — must produce
# WeeklyCourseData objects. The rest of the pipeline (AI client,
# storage) only knows about this schema, so it never changes when
# a new scraper is added.
#
# These are plain dataclasses: data containers with no logic.
# Think of them like structs in other languages.

from __future__ import annotations                    # allows list[X] syntax on older Python
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Assignment:
    # == Assignment == #
    # Represents one graded item found on an LMS course page.
    # Only `title` is required; everything else may be absent from the page.

    title: str                                        # e.g. "Homework 3: Recursion"
    due_date: datetime | None = None                  # UTC-aware; None if not found
    status: str | None = None                         # e.g. "Not Started", "Submitted"
    description: str | None = None                    # scraped detail text, if any
    url: str | None = None                            # direct link to the assignment
    points: float | None = None                       # point value, if listed


@dataclass
class WeeklyCourseData:
    # == WeeklyCourseData == #
    # The standard output contract every scraper must fulfill.
    # Changing the scraper never requires changing the AI client or storage
    # because they only ever see this type.

    course_name: str                                  # human-readable course title
    scraped_at: datetime                              # UTC-aware timestamp of the scrape

    # field(default_factory=list) is required for mutable defaults in dataclasses.
    # Writing `= []` here would cause all instances to share one list — a Python gotcha.
    assignments: list[Assignment] = field(default_factory=list)
    announcements: list[str] = field(default_factory=list)

    raw_notes: str = ""                               # freeform pass-through text
    scraper_name: str = ""                            # e.g. "d2l", "canvas"
