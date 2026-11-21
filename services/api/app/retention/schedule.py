from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.time import utcnow
from app.models.entities import LearningSession
from app.models.retention import RevisionReview
from app.retention import policy as retention_policy


def schedule_after_mastery(db: Session, learning_session: LearningSession, objective_code: str) -> RevisionReview:
    intervals, zone = _rules()
    anchor = retention_policy.local_date(retention_policy.current_time(), zone)
    due_on, index = retention_policy.next_due_on(anchor, 0, intervals)
    existing = _open_review(db, learning_session.id, objective_code)
    now = utcnow()
    if existing is not None and existing.status == "scheduled":
        existing.due_on = due_on
        existing.interval_index = index
        existing.timezone = zone
        existing.updated_at = now
        db.flush()
        return existing
    if existing is not None:
        return existing
    row = RevisionReview(
        session_id=learning_session.id,
        learner_id=learning_session.learner_id,
        topic_id=learning_session.topic_id,
        objective_code=objective_code,
        interval_index=index,
        due_on=due_on,
        timezone=zone,
        status="scheduled",
        was_missed=False,
        rubric=[],
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def schedule_following(
    db: Session,
    learning_session: LearningSession,
    objective_code: str,
    interval_index: int,
) -> RevisionReview:
    intervals, zone = _rules()
    anchor = retention_policy.local_date(retention_policy.current_time(), zone)
    due_on, index = retention_policy.next_due_on(anchor, interval_index, intervals)
    now = utcnow()
    row = RevisionReview(
        session_id=learning_session.id,
        learner_id=learning_session.learner_id,
        topic_id=learning_session.topic_id,
        objective_code=objective_code,
        interval_index=index,
        due_on=due_on,
        timezone=zone,
        status="scheduled",
        was_missed=False,
        rubric=[],
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def _rules() -> tuple[tuple[int, ...], str]:
    settings = get_settings()
    try:
        return retention_policy.parse_intervals(settings.retention_intervals_days), settings.retention_timezone
    except ValueError as exc:
        raise AppError("validation_error", str(exc), 422) from None


def _open_review(db: Session, session_id, objective_code: str) -> RevisionReview | None:
    return db.scalar(
        select(RevisionReview).where(
            RevisionReview.session_id == session_id,
            RevisionReview.objective_code == objective_code,
            RevisionReview.status.in_(("scheduled", "in_progress")),
        )
    )
