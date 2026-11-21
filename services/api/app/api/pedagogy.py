from fastapi import APIRouter

from app.core.errors import AppError
from app.pedagogy.registry import RegistryValidationError, load_registry, production_selectable_strategy_ids
from app.schemas.pedagogy import RegistryRead

router = APIRouter(prefix="/pedagogy", tags=["pedagogy"])


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
