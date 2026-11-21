from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models import User
from app.planner import service as plans
from app.schemas.planning import ConceptRead, LearningPlanRead
from app.services import sessions as session_service

topics = APIRouter(prefix="/topics", tags=["planning"])
sessions = APIRouter(prefix="/sessions", tags=["planning"])


def _owned_session(db: Session, user: User, session_id: UUID):
    item = session_service.get_session(db, session_id)
    if user.profile is None or item.learner_id != user.profile.id:
        raise NotFoundError("session_not_found", "Learning session was not found.")
    return item


@topics.get("/{topic_id}/concepts", response_model=list[ConceptRead])
def get_concepts(
    topic_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> list[ConceptRead]:
    del user
    return plans.list_concepts(db, topic_id)


@sessions.post("/{session_id}/plan", response_model=LearningPlanRead, status_code=201)
def post_plan(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> LearningPlanRead:
    item = _owned_session(db, user, session_id)
    return plans.create_plan(db, item)


@sessions.get("/{session_id}/plan", response_model=LearningPlanRead)
def get_plan(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> LearningPlanRead:
    item = _owned_session(db, user, session_id)
    return plans.get_plan(db, item)


@sessions.post("/{session_id}/plan/revision", response_model=LearningPlanRead)
def post_revision(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> LearningPlanRead:
    item = _owned_session(db, user, session_id)
    return plans.revise_plan(db, item)
