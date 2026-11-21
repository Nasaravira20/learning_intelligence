from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import AiModelCheck

STRUCTURED_CHECK = {
    "diagnostic": "structured_diagnostic",
    "teaching": "structured_teaching",
    "evaluation": "structured_evaluation",
}


def latest_check(session: Session, model_id: str, check_name: str) -> AiModelCheck | None:
    return session.scalar(
        select(AiModelCheck)
        .where(AiModelCheck.model_id == model_id, AiModelCheck.check_name == check_name)
        .order_by(AiModelCheck.checked_at.desc(), AiModelCheck.id.desc())
    )


def verified_model_ids(session: Session, task: str) -> list[str]:
    check_name = STRUCTURED_CHECK.get(task)
    if check_name is None:
        return []
    model_ids = session.scalars(select(AiModelCheck.model_id).distinct()).all()
    verified: list[str] = []
    for model_id in model_ids:
        generation = latest_check(session, model_id, "generation")
        structured = latest_check(session, model_id, check_name)
        if generation is not None and generation.status == "passed" and structured is not None and structured.status == "passed":
            verified.append(model_id)
    return verified


def require_model(session: Session, task: str) -> str:
    verified = verified_model_ids(session, task)
    if not verified:
        raise AppError(
            "model_not_verified",
            "No model has passed a live generation and structured-output check for this task.",
            503,
        )
    return verified[0]
