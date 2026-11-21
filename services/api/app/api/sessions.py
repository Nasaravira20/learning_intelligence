from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import optional_user
from app.core.errors import AppError, NotFoundError
from app.db.session import get_db
from app.models import User
from app.schemas.learner import SessionHistoryRead
from app.schemas.resources import SessionCreate, SessionRead
from app.services import learner_intelligence as intelligence
from app.services import sessions as session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _learner_id(user: User | None) -> UUID | None:
    if user is None or user.profile is None:
        return None
    return user.profile.id


def _visible(item, user: User | None):
    owner_id = _learner_id(user)
    if owner_id is not None and item.learner_id != owner_id:
        raise NotFoundError("session_not_found", "Learning session was not found.")
    return item


@router.post("", response_model=SessionRead, status_code=201)
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    user: User | None = Depends(optional_user),
) -> SessionRead:
    learner_id = _learner_id(user) or payload.learner_id
    item = session_service.create_session(db, learner_id, payload.topic_id)
    return session_service.to_session_read(item)


@router.get("", response_model=list[SessionRead])
def list_sessions(
    db: Session = Depends(get_db),
    user: User | None = Depends(optional_user),
) -> list[SessionRead]:
    items = session_service.list_sessions(db, _learner_id(user))
    return [session_service.to_session_read(item) for item in items]


@router.get("/{session_id}/history", response_model=SessionHistoryRead)
def session_history(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User | None = Depends(optional_user),
) -> SessionHistoryRead:
    if user is None or user.profile is None:
        raise AppError("unauthenticated", "Sign in to continue.", 401)
    item = session_service.get_session(db, session_id)
    if item.learner_id != user.profile.id:
        raise NotFoundError("session_not_found", "Learning session was not found.")
    return intelligence.history_for_session(db, item)


@router.get("/{session_id}", response_model=SessionRead)
def get_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User | None = Depends(optional_user),
) -> SessionRead:
    item = _visible(session_service.get_session(db, session_id), user)
    return session_service.to_session_read(item)


@router.post("/{session_id}/resume", response_model=SessionRead)
def resume_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User | None = Depends(optional_user),
) -> SessionRead:
    item = _visible(session_service.get_session(db, session_id), user)
    resumed = session_service.resume_session(db, item.id)
    return session_service.to_session_read(resumed)
