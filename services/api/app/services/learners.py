import logging
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.logging import log_event
from app.models import LearnerProfile, User

logger = logging.getLogger(__name__)


def create_learner(session: Session, display_name: str) -> LearnerProfile:
    user = User(id=uuid4())
    profile = LearnerProfile(id=uuid4(), user_id=user.id, display_name=display_name)
    session.add(user)
    session.add(profile)
    session.flush()
    log_event(logger, logging.INFO, "learner_created", learner_id=profile.id)
    return profile


def get_learner(session: Session, learner_id: UUID) -> LearnerProfile:
    profile = session.get(LearnerProfile, learner_id)
    if profile is None:
        log_event(logger, logging.WARNING, "learner_not_found", learner_id=learner_id)
        raise NotFoundError("learner_not_found", "Learner was not found.")
    return profile


def list_learners(session: Session) -> list[LearnerProfile]:
    statement = select(LearnerProfile).order_by(LearnerProfile.created_at, LearnerProfile.id)
    return list(session.scalars(statement).all())
