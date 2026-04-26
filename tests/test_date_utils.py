# == test_date_utils.py == #
# Tests for core/date_utils.py.
# Written BEFORE the implementation — this is TDD.
# Run with:  pytest tests/test_date_utils.py -v

import pytest
from datetime import datetime, timezone, timedelta
from core.date_utils import parse_date, is_within_days


# == parse_date Tests == #

class TestParseDate:

    def _assert_utc(self, dt: datetime) -> None:
        # Every date returned by parse_date must be UTC-aware.
        assert dt.tzinfo is not None, "Returned datetime must be timezone-aware"
        assert dt.utcoffset() == timedelta(0), "Returned datetime must be UTC"

    def test_returns_none_on_empty_string(self):
        assert parse_date("") is None

    def test_returns_none_on_whitespace_only(self):
        assert parse_date("   ") is None

    def test_returns_none_on_garbage_input(self):
        assert parse_date("not a date at all!!!") is None

    def test_parses_iso_with_timezone(self):
        # datetime.fromisoformat handles this natively in Python 3.7+
        result = parse_date("2026-04-30T23:59:00+00:00")
        assert result is not None
        assert result.year == 2026
        assert result.month == 4
        assert result.day == 30
        self._assert_utc(result)

    def test_parses_iso_without_timezone(self):
        result = parse_date("2026-04-30T23:59:00")
        assert result is not None
        assert result.year == 2026
        self._assert_utc(result)

    def test_parses_abbreviated_month_with_time(self):
        # "Apr 30, 2026 11:59 PM" — common D2L format
        result = parse_date("Apr 30, 2026 11:59 PM")
        assert result is not None
        assert result.month == 4
        assert result.day == 30
        assert result.hour == 23
        self._assert_utc(result)

    def test_parses_full_month_with_time(self):
        # "April 30, 2026 11:59 PM"
        result = parse_date("April 30, 2026 11:59 PM")
        assert result is not None
        assert result.month == 4
        self._assert_utc(result)

    def test_parses_date_only_iso(self):
        result = parse_date("2026-04-30")
        assert result is not None
        assert result.year == 2026
        assert result.month == 4
        assert result.day == 30
        self._assert_utc(result)

    def test_parses_date_only_abbreviated_month(self):
        result = parse_date("Apr 30, 2026")
        assert result is not None
        assert result.month == 4
        self._assert_utc(result)

    def test_parses_us_format_with_time(self):
        # "04/30/2026 11:59 PM"
        result = parse_date("04/30/2026 11:59 PM")
        assert result is not None
        assert result.month == 4
        self._assert_utc(result)

    def test_parses_european_format(self):
        # "30/04/2026 23:59"
        result = parse_date("30/04/2026 23:59")
        assert result is not None
        assert result.day == 30
        assert result.month == 4
        self._assert_utc(result)

    def test_parses_datetime_with_seconds(self):
        result = parse_date("2026-04-30 23:59:00")
        assert result is not None
        assert result.second == 0
        self._assert_utc(result)

    def test_strips_whitespace_before_parsing(self):
        result = parse_date("  2026-04-30  ")
        assert result is not None
        assert result.year == 2026


# == is_within_days Tests == #

class TestIsWithinDays:

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def test_returns_false_for_none(self):
        assert is_within_days(None) is False

    def test_returns_true_for_date_tomorrow(self):
        tomorrow = self._now() + timedelta(days=1)
        assert is_within_days(tomorrow) is True

    def test_returns_true_for_date_in_6_days(self):
        in_six = self._now() + timedelta(days=6)
        assert is_within_days(in_six) is True

    def test_returns_false_for_date_in_8_days(self):
        in_eight = self._now() + timedelta(days=8)
        assert is_within_days(in_eight) is False

    def test_returns_false_for_past_date(self):
        yesterday = self._now() - timedelta(days=1)
        assert is_within_days(yesterday) is False

    def test_custom_days_window(self):
        in_14 = self._now() + timedelta(days=14)
        assert is_within_days(in_14, days=7) is False
        assert is_within_days(in_14, days=15) is True

    def test_date_exactly_at_boundary(self):
        # A date exactly 7 days from now should be included.
        exactly_7 = self._now() + timedelta(days=7)
        assert is_within_days(exactly_7) is True
