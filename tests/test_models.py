# == test_models.py == #
# Tests for core/models.py.
# Written BEFORE the implementation — this is TDD.
# Run with:  pytest tests/test_models.py -v

import pytest
from datetime import datetime, timezone
from core.models import Assignment, WeeklyCourseData


# == Assignment Tests == #

class TestAssignment:

    def test_requires_only_title(self):
        # All fields except title are optional.
        a = Assignment(title="Homework 1")
        assert a.title == "Homework 1"
        assert a.due_date is None
        assert a.status is None
        assert a.description is None
        assert a.url is None
        assert a.points is None

    def test_accepts_all_fields(self):
        due = datetime(2026, 4, 30, 23, 59, tzinfo=timezone.utc)
        a = Assignment(
            title="Final Project",
            due_date=due,
            status="Not Started",
            description="Write a 10-page report",
            url="https://example.com/assignments/1",
            points=100.0,
        )
        assert a.due_date == due
        assert a.status == "Not Started"
        assert a.points == 100.0

    def test_two_instances_are_independent(self):
        # Basic sanity: two Assignment objects are separate objects.
        a1 = Assignment(title="A1")
        a2 = Assignment(title="A2")
        assert a1 is not a2
        assert a1.title != a2.title


# == WeeklyCourseData Tests == #

class TestWeeklyCourseData:

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def test_requires_course_name_and_scraped_at(self):
        now = self._now()
        wcd = WeeklyCourseData(course_name="COMP 101", scraped_at=now)
        assert wcd.course_name == "COMP 101"
        assert wcd.scraped_at == now

    def test_assignments_default_to_empty_list(self):
        wcd = WeeklyCourseData(course_name="X", scraped_at=self._now())
        assert wcd.assignments == []

    def test_announcements_default_to_empty_list(self):
        wcd = WeeklyCourseData(course_name="X", scraped_at=self._now())
        assert wcd.announcements == []

    def test_raw_notes_defaults_to_empty_string(self):
        wcd = WeeklyCourseData(course_name="X", scraped_at=self._now())
        assert wcd.raw_notes == ""

    def test_scraper_name_defaults_to_empty_string(self):
        wcd = WeeklyCourseData(course_name="X", scraped_at=self._now())
        assert wcd.scraper_name == ""

    def test_two_instances_do_not_share_assignment_list(self):
        # This catches the classic Python mutable-default-argument bug.
        # field(default_factory=list) prevents both instances from pointing
        # at the same list object.
        now = self._now()
        w1 = WeeklyCourseData(course_name="C1", scraped_at=now)
        w2 = WeeklyCourseData(course_name="C2", scraped_at=now)
        w1.assignments.append(Assignment(title="HW1"))
        assert len(w2.assignments) == 0, "Modifying w1.assignments must not affect w2"

    def test_two_instances_do_not_share_announcements_list(self):
        now = self._now()
        w1 = WeeklyCourseData(course_name="C1", scraped_at=now)
        w2 = WeeklyCourseData(course_name="C2", scraped_at=now)
        w1.announcements.append("Test announcement")
        assert len(w2.announcements) == 0

    def test_can_add_assignments(self):
        wcd = WeeklyCourseData(course_name="COMP 101", scraped_at=self._now())
        wcd.assignments.append(Assignment(title="Quiz 1", points=20.0))
        assert len(wcd.assignments) == 1
        assert wcd.assignments[0].title == "Quiz 1"

    def test_scraped_at_is_timezone_aware(self):
        # All datetimes in this project must carry timezone info.
        # A naive datetime (no tzinfo) is treated as a bug.
        now = datetime.now(timezone.utc)
        wcd = WeeklyCourseData(course_name="X", scraped_at=now)
        assert wcd.scraped_at.tzinfo is not None
