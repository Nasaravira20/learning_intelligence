from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.providers.base import ModelProvider
from app.api.deps import get_model_provider, require_user
from app.core.errors import AppError
from app.api.pedagogy import _owned_session
from app.db.session import get_db
from app.models import User
from app.retention import service as retention_service
from app.schemas.retention import ResponseInput, RetentionRead, ReviewRead

router = APIRouter(tags=["retention"])
sessions = APIRouter(prefix="/sessions", tags=["retention"])


@router.get("/retention", response_model=list[ReviewRead])
def get_reviews(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> list[ReviewRead]:
    if user.profile is None:
        raise AppError("unauthenticated", "Sign in to continue.", 401)
    return retention_service.list_reviews(db, user.profile.id)


@sessions.get("/{session_id}/retention", response_model=RetentionRead)
def get_session_retention(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> RetentionRead:
    item = _owned_session(db, user, session_id)
    return retention_service.get_retention(db, item)


@sessions.post("/{session_id}/retention", response_model=ReviewRead, status_code=201)
def post_retention(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    provider: ModelProvider = Depends(get_model_provider),
) -> ReviewRead:
    item = _owned_session(db, user, session_id)
    return retention_service.start_review(db, item, provider)


@sessions.post("/{session_id}/retention/response", response_model=ReviewRead)
def post_response(
    session_id: UUID,
    payload: ResponseInput,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    provider: ModelProvider = Depends(get_model_provider),
) -> ReviewRead:
    item = _owned_session(db, user, session_id)
    return retention_service.submit_review(db, item, provider, payload)
