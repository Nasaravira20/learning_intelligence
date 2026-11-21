import logging
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.core.logging import log_event
from app.db.errors import translate_integrity_error
from app.models import LearningTopic

logger = logging.getLogger(__name__)


def create_topic(
    session: Session,
    title: str,
    slug: str,
    description: str | None,
) -> LearningTopic:
    existing = session.scalar(select(LearningTopic.id).where(LearningTopic.slug == slug))
    if existing is not None:
        log_event(logger, logging.WARNING, "topic_slug_taken", slug=slug)
        raise ConflictError("topic_slug_taken", "A topic with this slug already exists.")

    topic = LearningTopic(id=uuid4(), title=title, slug=slug, description=description)
    session.add(topic)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        translated = translate_integrity_error(exc)
        log_event(logger, logging.WARNING, "topic_conflict", code=translated.code, slug=slug)
        raise translated from exc

    log_event(logger, logging.INFO, "topic_created", topic_id=topic.id)
    return topic


def get_topic(session: Session, topic_id: UUID) -> LearningTopic:
    topic = session.get(LearningTopic, topic_id)
    if topic is None:
        log_event(logger, logging.WARNING, "topic_not_found", topic_id=topic_id)
        raise NotFoundError("topic_not_found", "Topic was not found.")
    return topic


def list_topics(session: Session) -> list[LearningTopic]:
    statement = select(LearningTopic).order_by(LearningTopic.created_at, LearningTopic.id)
    return list(session.scalars(statement).all())
