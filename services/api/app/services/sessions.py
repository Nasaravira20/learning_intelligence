import logging
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError, NotFoundError
from app.core.logging import log_event
from app.core.time import utcnow
from app.models import LearningSession
from app.schemas.resources import SessionRead
from app.services.learners import get_learner
from app.services.topics import get_topic

logger = logging.getLogger(__name__)


def to_session_read(item: LearningSession) -> SessionRead:
    return SessionRead(
        id=item.id,
        learner_id=item.learner_id,
        topic_id=item.topic_id,
        learner_name=item.learner.display_name,
        topic_title=item.topic.title,
        topic_slug=item.topic.slug,
        status=item.status,
        created_at=item.created_at,
        updated_at=item.updated_at,
        resumed_at=item.resumed_at,
    )


def _load_statement():
    return select(LearningSession).options(
        joinedload(LearningSession.learner),
        joinedload(LearningSession.topic),
    )


def create_session(session: Session, learner_id: UUID, topic_id: UUID) -> LearningSession:
    learner = get_learner(session, learner_id)
    topic = get_topic(session, topic_id)
    learning_session = LearningSession(
        id=uuid4(),
        learner_id=learner.id,
        topic_id=topic.id,
        status="TOPIC_SELECTED",
    )
    learning_session.learner = learner
    learning_session.topic = topic
    session.add(learning_session)
    session.flush()
    log_event(
        logger,
        logging.INFO,
        "session_created",
        session_id=learning_session.id,
        learner_id=learner.id,
        topic_id=topic.id,
    )
    return learning_session


def get_session(session: Session, session_id: UUID) -> LearningSession:
    item = session.scalar(_load_statement().where(LearningSession.id == session_id))
    if item is None:
        log_event(logger, logging.WARNING, "session_not_found", session_id=session_id)
        raise NotFoundError("session_not_found", "Learning session was not found.")
    return item


def list_sessions(session: Session, learner_id: UUID | None = None) -> list[LearningSession]:
    statement = _load_statement().order_by(LearningSession.created_at.desc(), LearningSession.id.desc())
    if learner_id is not None:
        statement = statement.where(LearningSession.learner_id == learner_id)
    return list(session.scalars(statement).unique().all())


def enter_diagnosis(session: Session, item: LearningSession) -> LearningSession:
    if item.status == "DIAGNOSING":
        return item
    if item.status != "TOPIC_SELECTED":
        raise AppError("invalid_transition", "This session cannot start a diagnosis.", 409)
    item.status = "DIAGNOSING"
    item.updated_at = utcnow()
    session.flush()
    log_event(
        logger,
        logging.INFO,
        "session_status_changed",
        session_id=item.id,
        status=item.status,
    )
    return item


def enter_plan(session: Session, item: LearningSession) -> LearningSession:
    if item.status == "PLAN_READY":
        return item
    if item.status != "DIAGNOSING":
        raise AppError("invalid_transition", "This session cannot open a learning plan.", 409)
    item.status = "PLAN_READY"
    item.updated_at = utcnow()
    session.flush()
    log_event(
        logger,
        logging.INFO,
        "session_status_changed",
        session_id=item.id,
        status=item.status,
    )
    return item


def resume_session(session: Session, session_id: UUID) -> LearningSession:
    item = get_session(session, session_id)
    now = utcnow()
    item.resumed_at = now
    item.updated_at = now
    session.flush()
    log_event(
        logger,
        logging.INFO,
        "session_resumed",
        session_id=item.id,
        status=item.status,
    )
    return item
