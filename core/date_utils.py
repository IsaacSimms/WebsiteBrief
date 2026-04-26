# == date_utils.py == #
# Stdlib-only date parsing and filtering utilities.
#
# No third-party libraries — everything uses Python's built-in datetime module.
#
# ADDING A NEW DATE FORMAT:
#   Append a strptime format string to DATE_FORMATS below.
#   parse_date() will try it automatically. No other changes needed.

from __future__ import annotations
from datetime import datetime, timezone, timedelta


# == DATE_FORMATS == #
# Tried in order. First match wins. fromisoformat() is tried before this list.
# Add new formats at the end to avoid changing existing behaviour.
DATE_FORMATS: list[str] = [
    "%b %d, %Y %I:%M %p",      # "Apr 30, 2026 11:59 PM"    — common D2L short month
    "%B %d, %Y %I:%M %p",      # "April 30, 2026 11:59 PM"  — D2L full month
    "%Y-%m-%dT%H:%M:%S",       # "2026-04-30T23:59:00"      — ISO 8601 (no offset)
    "%Y-%m-%d %H:%M:%S",       # "2026-04-30 23:59:00"
    "%Y-%m-%d %H:%M",          # "2026-04-30 23:59"
    "%m/%d/%Y %I:%M %p",       # "04/30/2026 11:59 PM"      — US format
    "%d/%m/%Y %H:%M",          # "30/04/2026 23:59"          — European format
    "%Y-%m-%d",                # "2026-04-30"               — date only
    "%b %d, %Y",               # "Apr 30, 2026"             — date only, short month
]


def parse_date(raw: str) -> datetime | None:
    # == parse_date == #
    # Try fromisoformat first (handles full ISO 8601 with UTC offsets like +00:00).
    # Then walk DATE_FORMATS until one matches.
    # Returns a UTC-aware datetime, or None if nothing matched.
    #
    # Why always UTC?  Storing everything as UTC avoids timezone comparison bugs.
    # "Is this assignment due in the next 7 days?" becomes a simple subtraction
    # when both sides are UTC-aware.

    raw = raw.strip()
    if not raw:
        return None

    try:
        dt = datetime.fromisoformat(raw)
        # fromisoformat may return a naive datetime (no tzinfo) for strings
        # like "2026-04-30T23:59:00" — treat those as UTC.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass

    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None    # no format matched


def is_within_days(dt: datetime | None, days: int = 7) -> bool:
    # == is_within_days == #
    # Return True if dt is between right now and `days` days from now (inclusive).
    # Returns False for None (can't filter what we don't have).
    #
    # Used in run.py to strip assignments that are already past or too far out
    # before building the AI prompt — keeps the prompt short and the API cheap.

    if dt is None:
        return False
    now = datetime.now(timezone.utc)
    return now <= dt <= now + timedelta(days=days)
