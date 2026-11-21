from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.time import utcnow

INTERVALS = (1, 3, 7, 16, 35)

RUBRIC = (
    "Recall the objective before any answer is shown.",
    "Score the answer separately from the reasoning.",
    "A correct answer with weak reasoning does not extend the review interval.",
    "A missed date is still reviewed, and the next interval starts again.",
    "A failed recall returns to remediation rather than a longer gap.",
)


def current_time() -> datetime:
    return utcnow()


def parse_intervals(raw: str) -> tuple[int, ...]:
    parts = [item.strip() for item in raw.split(",") if item.strip()]
    if not parts or len(parts) > 8:
        raise ValueError("Retention intervals need between 1 and 8 day counts.")
    days: list[int] = []
    for item in parts:
        if not item.isdigit():
            raise ValueError("Retention intervals must be whole days.")
        value = int(item)
        if value < 1 or value > 365:
            raise ValueError("Each retention interval must be from 1 to 365 days.")
        if days and value < days[-1]:
            raise ValueError("Retention intervals must stay the same or grow.")
        days.append(value)
    return tuple(days)


def local_date(moment: datetime, zone: str) -> date:
    if moment.tzinfo is None:
        raise ValueError("A revision clock must include a timezone.")
    try:
        tz = ZoneInfo(zone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("The revision timezone is not a known IANA name.") from exc
    return moment.astimezone(tz).date()


def next_due_on(anchor: date, interval_index: int, intervals: tuple[int, ...]) -> tuple[date, int]:
    if not intervals:
        raise ValueError("Retention intervals are empty.")
    index = min(max(interval_index, 0), len(intervals) - 1)
    return anchor + timedelta(days=intervals[index]), index


def review_timing(due_on: date, moment: datetime, zone: str) -> str:
    today = local_date(moment, zone)
    if today < due_on:
        return "scheduled"
    if today == due_on:
        return "due"
    return "missed"


def index_after(*, interval_index: int, recalled: bool, missed: bool) -> int:
    if not recalled or missed:
        return 0
    return interval_index + 1
