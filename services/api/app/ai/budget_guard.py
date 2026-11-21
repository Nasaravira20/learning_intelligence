from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import AiUsageRecord

CATEGORY_CEILINGS = {
    "smoke": Decimal("1"),
    "development": Decimal("3"),
    "teaching": Decimal("5"),
    "evaluation": Decimal("5"),
    "demo": Decimal("4"),
}


def spent(session: Session, category: str | None = None) -> Decimal:
    statement = select(func.coalesce(func.sum(AiUsageRecord.estimated_cost_usd), 0))
    if category is not None:
        statement = statement.where(AiUsageRecord.category == category)
    total = session.scalar(statement)
    return Decimal(total or 0)


def ensure_allowed(session: Session, category: str, estimated_cost: Decimal) -> None:
    if category not in CATEGORY_CEILINGS:
        raise AppError("budget_exceeded", "That usage category is not allowed.", 429)
    settings = get_settings()
    total_after = spent(session) + estimated_cost
    category_after = spent(session, category) + estimated_cost
    if total_after > settings.gemini_budget_usd or category_after > CATEGORY_CEILINGS[category]:
        raise AppError(
            "budget_exceeded",
            "The internal Gemini budget has been reached. No further model call was sent.",
            429,
        )
