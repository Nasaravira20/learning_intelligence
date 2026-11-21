from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.request_context import get_request_id
from app.core.time import utcnow
from app.models import AiModelCheck, AiUsageRecord


def record_usage(
    session: Session,
    *,
    category: str,
    task: str,
    model_id: str,
    status: str,
    estimated_cost_usd: Decimal,
    action_id: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    latency_ms: int | None = None,
    error_class: str | None = None,
) -> AiUsageRecord:
    row = AiUsageRecord(
        id=uuid4(),
        created_at=utcnow(),
        category=category,
        task=task,
        model_id=model_id,
        status=status,
        action_id=action_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        estimated_cost_usd=estimated_cost_usd,
        error_class=error_class,
        request_id=get_request_id(),
    )
    session.add(row)
    session.flush()
    return row


def attempts_for_action(session: Session, action_id: str) -> int:
    total = session.scalar(
        select(func.count())
        .select_from(AiUsageRecord)
        .where(AiUsageRecord.action_id == action_id, AiUsageRecord.status != "blocked")
    )
    return int(total or 0)


def record_check(
    session: Session,
    *,
    model_id: str,
    check_name: str,
    status: str,
    error_class: str | None = None,
    latency_ms: int | None = None,
) -> AiModelCheck:
    row = AiModelCheck(
        id=uuid4(),
        model_id=model_id,
        check_name=check_name,
        status=status,
        error_class=error_class,
        latency_ms=latency_ms,
        checked_at=utcnow(),
    )
    session.add(row)
    session.flush()
    return row
