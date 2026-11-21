from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.providers.base import ModelProvider
from app.api.deps import get_model_provider, require_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.diagnostics import service as diagnostics
from app.models import User
from app.schemas.diagnostics import DiagnosisReport, ObjectiveCreate, ObjectiveRead, ResponseBatch
from app.services import sessions as session_service

topics = APIRouter(prefix="/topics", tags=["diagnostics"])
sessions = APIRouter(prefix="/sessions", tags=["diagnostics"])


def _owned_session(db: Session, user: User, session_id: UUID):
    item = session_service.get_session(db, session_id)
    if user.profile is None or item.learner_id != user.profile.id:
        raise NotFoundError("session_not_found", "Learning session was not found.")
    return item


@topics.get("/{topic_id}/objectives", response_model=list[ObjectiveRead])
def list_objectives(
    topic_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> list[ObjectiveRead]:
    del user
    return diagnostics.list_objective_reads(db, topic_id)


@topics.post("/{topic_id}/objectives", response_model=ObjectiveRead, status_code=201)
def post_objective(
    topic_id: UUID,
    payload: ObjectiveCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> ObjectiveRead:
    del user
    return diagnostics.create_objective(db, topic_id, payload)


@sessions.post("/{session_id}/diagnosis", response_model=DiagnosisReport, status_code=201)
def post_diagnosis(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    provider: ModelProvider = Depends(get_model_provider),
) -> DiagnosisReport:
    item = _owned_session(db, user, session_id)
    return diagnostics.start_diagnosis(db, provider, item)


@sessions.get("/{session_id}/diagnosis", response_model=DiagnosisReport)
def get_diagnosis(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> DiagnosisReport:
    item = _owned_session(db, user, session_id)
    return diagnostics.get_diagnosis(db, item)


@sessions.post("/{session_id}/diagnosis/responses", response_model=DiagnosisReport)
def post_responses(
    session_id: UUID,
    payload: ResponseBatch,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    provider: ModelProvider = Depends(get_model_provider),
) -> DiagnosisReport:
    item = _owned_session(db, user, session_id)
    return diagnostics.submit_responses(db, provider, item, payload.responses)
