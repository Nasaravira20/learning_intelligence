from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_model_provider, require_user
from app.api.pedagogy import _owned_session
from app.ai.providers.base import ModelProvider
from app.db.session import get_db
from app.models import User
from app.schemas.teaching import AttemptInput, LessonRead
from app.teaching import service as teaching_service

sessions = APIRouter(prefix="/sessions", tags=["teaching"])


@sessions.post("/{session_id}/teaching", response_model=LessonRead, status_code=201)
def post_lesson(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    provider: ModelProvider = Depends(get_model_provider),
) -> LessonRead:
    item = _owned_session(db, user, session_id)
    return teaching_service.start_lesson(db, item, provider)


@sessions.get("/{session_id}/teaching", response_model=LessonRead)
def get_saved_lesson(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> LessonRead:
    item = _owned_session(db, user, session_id)
    return teaching_service.get_lesson(db, item)


@sessions.post("/{session_id}/teaching/hint", response_model=LessonRead)
def post_hint(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> LessonRead:
    item = _owned_session(db, user, session_id)
    return teaching_service.reveal_hint(db, item)


@sessions.post("/{session_id}/teaching/attempt", response_model=LessonRead)
def post_attempt(
    session_id: UUID,
    payload: AttemptInput,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> LessonRead:
    item = _owned_session(db, user, session_id)
    return teaching_service.record_attempt(db, item, payload)
