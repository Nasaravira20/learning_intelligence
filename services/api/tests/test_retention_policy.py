from datetime import date, datetime, timezone

import pytest

from app.retention.policy import (
    index_after,
    local_date,
    next_due_on,
    parse_intervals,
    review_timing,
)

UTC = timezone.utc
INTERVALS = (1, 3, 7, 16, 35)


def test_intervals_grow_and_reject_a_shorter_later_gap() -> None:
    assert parse_intervals("1,3,7,16,35") == INTERVALS
    with pytest.raises(ValueError):
        parse_intervals("7,3")
    with pytest.raises(ValueError):
        parse_intervals("0,1")


def test_due_date_uses_the_local_calendar_not_the_utc_date() -> None:
    learned = datetime(2026, 11, 21, 18, 30, tzinfo=UTC)
    assert local_date(learned, "UTC") == date(2026, 11, 21)
    assert local_date(learned, "Asia/Kolkata") == date(2026, 11, 22)
    utc_due, _index = next_due_on(local_date(learned, "UTC"), 0, INTERVALS)
    kolkata_due, _index = next_due_on(local_date(learned, "Asia/Kolkata"), 0, INTERVALS)
    assert utc_due == date(2026, 11, 22)
    assert kolkata_due == date(2026, 11, 23)
    still_twenty_second = datetime(2026, 11, 22, 18, 29, tzinfo=UTC)
    first_of_twenty_third = datetime(2026, 11, 22, 18, 30, tzinfo=UTC)
    assert review_timing(kolkata_due, still_twenty_second, "Asia/Kolkata") == "scheduled"
    assert review_timing(kolkata_due, first_of_twenty_third, "Asia/Kolkata") == "due"


def test_los_angeles_midnight_is_the_due_boundary() -> None:
    due_on = date(2026, 11, 22)
    before = datetime(2026, 11, 22, 7, 59, tzinfo=UTC)
    after = datetime(2026, 11, 22, 8, 0, tzinfo=UTC)
    assert review_timing(due_on, before, "America/Los_Angeles") == "scheduled"
    assert review_timing(due_on, after, "America/Los_Angeles") == "due"
    day_after = datetime(2026, 11, 23, 8, 0, tzinfo=UTC)
    assert review_timing(due_on, day_after, "America/Los_Angeles") == "missed"


def test_a_miss_or_a_failed_recall_does_not_extend_the_interval() -> None:
    assert index_after(interval_index=1, recalled=True, missed=False) == 2
    assert index_after(interval_index=1, recalled=True, missed=True) == 0
    assert index_after(interval_index=1, recalled=False, missed=False) == 0
