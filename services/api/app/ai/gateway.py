import logging
import time
from collections.abc import Callable
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.budget_guard import ensure_allowed
from app.ai.errors import ProviderError
from app.ai.model_registry import require_model, verified_model_ids
from app.ai.pricing import estimate_cost, worst_case_tokens
from app.ai.providers.base import ModelProvider
from app.ai.schemas import parse_model_json
from app.ai.types import GenerationRequest, GenerationResult
from app.ai.usage_tracker import attempts_for_action, record_usage
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import log_event

logger = logging.getLogger(__name__)

MESSAGES = {
    "timeout": "The model request timed out.",
    "network": "The model service could not be reached.",
    "rate_limit": "The model service rate limit was reached.",
    "unavailable": "The model service was unavailable.",
    "quota": "The model quota has been reached.",
    "invalid_key": "The model credential was rejected.",
    "permission": "The model credential is not allowed to perform that request.",
    "model_not_found": "The requested model is not available.",
    "unsupported_operation": "The model does not support that operation.",
    "malformed_output": "The model output did not match the required schema.",
    "unknown": "The model request failed.",
    "call_limit": "This action has used its model-call allowance.",
}


def _status_code(error_class: str) -> int:
    if error_class in {"invalid_key"}:
        return 401
    if error_class == "permission":
        return 403
    if error_class in {"rate_limit", "quota", "budget_exceeded", "call_limit"}:
        return 429
    if error_class == "malformed_output":
        return 422
    return 503


def _failure(error_class: str) -> AppError:
    return AppError(error_class, MESSAGES.get(error_class, MESSAGES["unknown"]), _status_code(error_class))


def generate(
    session: Session,
    provider: ModelProvider,
    *,
    task: str,
    category: str,
    prompt: str,
    output_model: type[BaseModel] | None = None,
    action_id: str | None = None,
    model_id: str | None = None,
    max_calls: int | None = None,
    sleeper: Callable[[float], None] = time.sleep,
) -> tuple[GenerationResult, BaseModel | None]:
    settings = get_settings()
    call_limit = settings.gemini_max_calls_per_action if max_calls is None else max_calls
    if len(prompt) > 4000:
        raise AppError("validation_error", "The model prompt is too long.", 422)
    if model_id is None:
        model_id = require_model(session, task)
    elif model_id not in verified_model_ids(session, task):
        raise AppError(
            "model_not_verified",
            "That model has not passed a live generation and structured-output check for this task.",
            503,
        )
    schema = output_model.model_json_schema() if output_model is not None else None
    request = GenerationRequest(
        model_id=model_id,
        prompt=prompt,
        max_output_tokens=settings.gemini_max_output_tokens,
        schema=schema,
    )
    input_estimate, output_estimate = worst_case_tokens(prompt, request.max_output_tokens)
    reserved = estimate_cost(input_estimate, output_estimate)
    attempts_allowed = settings.gemini_max_retries + 1

    for attempt in range(attempts_allowed):
        if action_id is not None and attempts_for_action(session, action_id) >= call_limit:
            record_usage(
                session,
                category=category,
                task=task,
                model_id=model_id,
                status="blocked",
                estimated_cost_usd=Decimal("0"),
                action_id=action_id,
                error_class="call_limit",
            )
            raise _failure("call_limit")
        try:
            ensure_allowed(session, category, reserved)
        except AppError as exc:
            record_usage(
                session,
                category=category,
                task=task,
                model_id=model_id,
                status="blocked",
                estimated_cost_usd=Decimal("0"),
                action_id=action_id,
                error_class=exc.code,
            )
            raise
        started = time.perf_counter()
        try:
            result = provider.generate(request)
        except ProviderError as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            record_usage(
                session,
                category=category,
                task=task,
                model_id=model_id,
                status="failed",
                estimated_cost_usd=reserved,
                action_id=action_id,
                latency_ms=latency_ms,
                error_class=exc.error_class,
            )
            log_event(
                logger,
                logging.WARNING,
                "model_request_failed",
                task=task,
                model_id=model_id,
                error_class=exc.error_class,
                latency_ms=latency_ms,
                estimated_cost_usd=str(reserved),
            )
            if exc.retryable and attempt + 1 < attempts_allowed:
                sleeper(0.25)
                continue
            raise _failure(exc.error_class) from None
        latency_ms = int((time.perf_counter() - started) * 1000)
        input_tokens = result.input_tokens if result.input_tokens is not None else input_estimate
        output_tokens = result.output_tokens if result.output_tokens is not None else output_estimate
        cost = estimate_cost(input_tokens, output_tokens)
        parsed: BaseModel | None = None
        if output_model is not None:
            try:
                parsed = parse_model_json(output_model, result.text)
            except ValueError:
                record_usage(
                    session,
                    category=category,
                    task=task,
                    model_id=result.model_id,
                    status="failed",
                    estimated_cost_usd=cost,
                    action_id=action_id,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    latency_ms=latency_ms,
                    error_class="malformed_output",
                )
                log_event(
                    logger,
                    logging.WARNING,
                    "model_output_rejected",
                    task=task,
                    model_id=result.model_id,
                    error_class="malformed_output",
                    latency_ms=latency_ms,
                    estimated_cost_usd=str(cost),
                )
                raise _failure("malformed_output") from None
        record_usage(
            session,
            category=category,
            task=task,
            model_id=result.model_id,
            status="succeeded",
            estimated_cost_usd=cost,
            action_id=action_id,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            latency_ms=latency_ms,
        )
        log_event(
            logger,
            logging.INFO,
            "model_request_completed",
            task=task,
            model_id=result.model_id,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            latency_ms=latency_ms,
            estimated_cost_usd=str(cost),
        )
        return result, parsed
    raise _failure("unknown")
