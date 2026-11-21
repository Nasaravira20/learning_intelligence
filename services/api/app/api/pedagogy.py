from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.core.errors import AppError, NotFoundError
from app.db.session import get_db
from app.models import User
from app.pedagogy import selection_service
from app.pedagogy.registry import RegistryValidationError, load_registry, production_selectable_strategy_ids
from app.schemas.pedagogy import RegistryRead, SelectionRead, SelectionRequest
from app.services import sessions as session_service

router = APIRouter(prefix="/pedagogy", tags=["pedagogy"])
sessions = APIRouter(prefix="/sessions", tags=["pedagogy"])


@router.get("/registry", response_model=RegistryRead)
def read_registry() -> RegistryRead:
    try:
        registry = load_registry()
    except RegistryValidationError as exc:
        raise AppError(
            code="registry_invalid",
            message="The pedagogy registry failed validation.",
            status_code=500,
            details=[{"field": issue.path, "message": issue.message} for issue in exc.issues],
        ) from exc
    return RegistryRead.from_registry(registry, production_selectable_strategy_ids(registry))


def _owned_session(db: Session, user: User, session_id: UUID):
    item = session_service.get_session(db, session_id)
    if user.profile is None or item.learner_id != user.profile.id:
        raise NotFoundError("session_not_found", "Learning session was not found.")
    return item


@sessions.post("/{session_id}/pedagogy-selection", response_model=SelectionRead, status_code=201)
def post_selection(
    session_id: UUID,
    payload: SelectionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> SelectionRead:
    item = _owned_session(db, user, session_id)
    return selection_service.record_selection(db, item, payload.context)


@sessions.get("/{session_id}/pedagogy-selection", response_model=SelectionRead)
def get_saved_selection(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> SelectionRead:
    item = _owned_session(db, user, session_id)
    return selection_service.get_selection(db, item)
