from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.providers.base import ModelProvider
from app.api.deps import get_model_provider, require_user
from app.api.pedagogy import _owned_session
from app.db.session import get_db
from app.evaluation import service as evaluation_service
from app.models import User
from app.schemas.evaluation import EvaluationRead, ResponseInput

sessions = APIRouter(prefix="/sessions", tags=["evaluation"])


@sessions.post("/{session_id}/evaluation", response_model=EvaluationRead, status_code=201)
def post_evaluation(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    provider: ModelProvider = Depends(get_model_provider),
) -> EvaluationRead:
    item = _owned_session(db, user, session_id)
    return evaluation_service.start_evaluation(db, item, provider)


@sessions.get("/{session_id}/evaluation", response_model=EvaluationRead)
def get_saved_evaluation(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> EvaluationRead:
    item = _owned_session(db, user, session_id)
    return evaluation_service.get_evaluation(db, item)


@sessions.post("/{session_id}/evaluation/response", response_model=EvaluationRead)
def post_response(
    session_id: UUID,
    payload: ResponseInput,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    provider: ModelProvider = Depends(get_model_provider),
) -> EvaluationRead:
    item = _owned_session(db, user, session_id)
    return evaluation_service.submit_response(db, item, provider, payload)


@sessions.post("/{session_id}/evaluation/remediation", response_model=EvaluationRead)
def post_remediation(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    provider: ModelProvider = Depends(get_model_provider),
) -> EvaluationRead:
    item = _owned_session(db, user, session_id)
    return evaluation_service.start_remediation(db, item, provider)
