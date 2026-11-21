import time
from pathlib import Path

from sqlalchemy.orm import Session

from app.ai.budget_guard import ensure_allowed, spent
from app.ai.errors import ProviderError
from app.ai.model_capabilities import select_candidates, text_model_ids
from app.ai.model_registry import verified_model_ids
from app.ai.pricing import estimate_cost, worst_case_tokens
from app.ai.prompts import GENERATION_PROBE, STRUCTURED_PROMPTS
from app.ai.providers.base import ModelProvider
from app.ai.schemas import STRUCTURED_TASKS, parse_model_json
from app.ai.types import GenerationRequest
from app.ai.usage_tracker import record_check, record_usage
from app.core.config import get_settings
from app.core.errors import AppError

PROBE_TOKENS = 256


def _attempt(
    session: Session,
    provider: ModelProvider,
    request: GenerationRequest,
    *,
    task: str,
) -> tuple[str, str | None, int]:
    input_estimate, output_estimate = worst_case_tokens(request.prompt, request.max_output_tokens)
    reserved = estimate_cost(input_estimate, output_estimate)
    try:
        ensure_allowed(session, "smoke", reserved)
    except AppError:
        record_usage(
            session,
            category="smoke",
            task=task,
            model_id=request.model_id,
            status="blocked",
            estimated_cost_usd=0,
            error_class="budget_exceeded",
        )
        return "failed", "budget_exceeded", 0
    started = time.perf_counter()
    try:
        result = provider.generate(request)
    except ProviderError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        record_usage(
            session,
            category="smoke",
            task=task,
            model_id=request.model_id,
            status="failed",
            estimated_cost_usd=reserved,
            latency_ms=latency_ms,
            error_class=exc.error_class,
        )
        return "failed", exc.error_class, latency_ms
    latency_ms = int((time.perf_counter() - started) * 1000)
    input_tokens = result.input_tokens if result.input_tokens is not None else input_estimate
    output_tokens = result.output_tokens if result.output_tokens is not None else output_estimate
    error_class = _probe_error(task, request, result.text)
    record_usage(
        session,
        category="smoke",
        task=task,
        model_id=result.model_id,
        status="failed" if error_class else "succeeded",
        estimated_cost_usd=estimate_cost(input_tokens, output_tokens),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        latency_ms=latency_ms,
        error_class=error_class,
    )
    if error_class:
        return "failed", error_class, latency_ms
    return "passed", None, latency_ms


def _probe_error(task: str, request: GenerationRequest, text: str) -> str | None:
    if request.schema is None:
        if "ready" not in text.lower():
            return "malformed_output"
        return None
    task_name = task.removeprefix("structured_")
    try:
        parse_model_json(STRUCTURED_TASKS[task_name], text)
    except ValueError:
        return "malformed_output"
    return None


def render_strategy(session: Session, listed: list[str], untested: list[str]) -> str:
    lines = [
        "# Gemini model strategy",
        "",
        "Costs below are internal estimates for the budget guard. They are not a provider invoice.",
        "A model is usable only after a live generation check and the structured check for that task both passed.",
        "Listing a model does not make it usable.",
        "",
        "The client uses the Gemini Interactions API. `response_format` carries the JSON schema.",
        "",
        f"Estimated smoke spend recorded: USD {spent(session, 'smoke')}",
        f"Estimated total spend recorded: USD {spent(session)}",
        "",
        "## Listed by the configured key",
        "",
    ]
    if listed:
        lines.extend(f"- `{model_id}`" for model_id in listed)
    else:
        lines.append("- None.")
    lines.extend(["", "## Not sent a generation request", ""])
    if untested:
        lines.extend(f"- `{model_id}`" for model_id in untested)
    else:
        lines.append("- None.")
    lines.extend(["", "## Usable after live checks", ""])
    any_usable = False
    for task in ("diagnostic", "teaching", "evaluation"):
        verified = verified_model_ids(session, task)
        if verified:
            any_usable = True
        rendered = ", ".join(f"`{model_id}`" for model_id in verified) or "None."
        lines.append(f"- {task}: {rendered}")
    if not any_usable:
        lines.extend(["", "No model is usable yet."])
    lines.append("")
    return "\n".join(lines)


def configuration_problem() -> str | None:
    if not get_settings().gemini_api_key:
        return "GEMINI_API_KEY is not configured. No model is usable."
    return None


def run_verification(
    session: Session,
    provider: ModelProvider,
    strategy_path: Path,
    *,
    configured: list[str] | None = None,
    limit: int | None = None,
) -> int:
    settings = get_settings()
    try:
        listed = provider.list_models()
    except ProviderError as exc:
        strategy_path.parent.mkdir(parents=True, exist_ok=True)
        strategy_path.write_text(
            "\n".join(
                [
                    "# Gemini model strategy",
                    "",
                    "The model list request failed.",
                    f"Error class: `{exc.error_class}`.",
                    "",
                    "No model is usable.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return 1
    for info in listed:
        record_check(session, model_id=info.model_id, check_name="listed", status="passed")
    if configured is None:
        configured = [item.strip() for item in settings.gemini_model_candidates.split(",") if item.strip()]
    verify_limit = settings.gemini_verify_limit if limit is None else limit
    explicit = bool(configured)
    candidates, missing = select_candidates(listed, configured, verify_limit)
    for model_id in missing:
        record_check(session, model_id=model_id, check_name="generation", status="failed", error_class="model_not_found")
    queue = candidates if explicit else text_model_ids(listed)
    stop_after_responses = len(queue) if explicit else verify_limit
    max_attempts = len(queue) if explicit else max(verify_limit * 3, verify_limit)
    attempted: list[str] = []
    responses = 0
    full_pass = False
    for model_id in queue:
        if responses >= stop_after_responses or len(attempted) >= max_attempts:
            break
        attempted.append(model_id)
        request = GenerationRequest(model_id=model_id, prompt=GENERATION_PROBE, max_output_tokens=PROBE_TOKENS)
        status, error_class, latency_ms = _attempt(session, provider, request, task="generation")
        record_check(
            session,
            model_id=model_id,
            check_name="generation",
            status=status,
            error_class=error_class,
            latency_ms=latency_ms,
        )
        if error_class == "model_not_found":
            continue
        responses += 1
        if status != "passed":
            continue
        structured_ok = True
        for task, model in STRUCTURED_TASKS.items():
            structured_request = GenerationRequest(
                model_id=model_id,
                prompt=STRUCTURED_PROMPTS[task],
                max_output_tokens=PROBE_TOKENS,
                schema=model.model_json_schema(),
            )
            structured_status, structured_error, structured_latency = _attempt(
                session,
                provider,
                structured_request,
                task=f"structured_{task}",
            )
            record_check(
                session,
                model_id=model_id,
                check_name=f"structured_{task}",
                status=structured_status,
                error_class=structured_error,
                latency_ms=structured_latency,
            )
            structured_ok = structured_ok and structured_status == "passed"
        full_pass = full_pass or structured_ok
    attempted_set = set(attempted) | set(missing)
    untested = [info.model_id for info in listed if info.model_id not in attempted_set]
    strategy_path.parent.mkdir(parents=True, exist_ok=True)
    strategy_path.write_text(render_strategy(session, [info.model_id for info in listed], untested), encoding="utf-8")
    return 0 if full_pass else 1
