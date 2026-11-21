import logging
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.ai.classify import provider_error_from_exception
from app.ai.errors import ProviderError
from app.ai.gateway import generate
from app.ai.model_capabilities import select_candidates
from app.ai.model_registry import verified_model_ids
from app.ai.providers.mock import MockProvider
from app.ai.schemas import DiagnosticProbe
from app.ai.types import GenerationResult, ModelInfo
from app.ai.usage_tracker import record_check, record_usage
from app.ai.verification import configuration_problem, run_verification
from app.core.errors import AppError
from app.core.logging import JsonFormatter, RequestIdFilter
from app.models import AiUsageRecord


class CollectHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(self.format(record))


def _capture_logs() -> CollectHandler:
    handler = CollectHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())
    logging.getLogger().addHandler(handler)
    return handler


@pytest.fixture
def db(client):
    from app.db.session import get_sessionmaker

    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _verified(session, model_id: str = "model-a") -> None:
    for check_name in ("generation", "structured_diagnostic", "structured_teaching", "structured_evaluation"):
        record_check(session, model_id=model_id, check_name=check_name, status="passed")


def _json_result(text: str) -> GenerationResult:
    return GenerationResult(text=text, model_id="model-a", input_tokens=8, output_tokens=6)


def test_error_classification_hides_the_key() -> None:
    class FakeApiError(Exception):
        def __init__(self) -> None:
            super().__init__("hidden")
            self.code = 401
            self.status = "UNAUTHENTICATED"
            self.message = "API key AIzaFakeKeyValueShouldNotLeak1234 is invalid"
            self.details = {"error": {"code": "authentication"}}

    error = provider_error_from_exception(FakeApiError())
    assert error.error_class == "invalid_key"
    assert error.retryable is False
    assert "AIza" not in str(error)
    assert provider_error_from_exception(TimeoutError()).error_class == "timeout"

    class FakeNotFound(Exception):
        def __init__(self) -> None:
            super().__init__("Error code: 404 - {'error': {'code': 'not_found'}}")

    assert provider_error_from_exception(FakeNotFound()).error_class == "model_not_found"


def test_candidate_selection_uses_only_listed_models() -> None:
    listed = [
        ModelInfo("model-a", ("generateContent",)),
        ModelInfo("text-embedding", ("embedContent",)),
    ]
    chosen, missing = select_candidates(listed, ["missing-model", "model-a"], limit=3)
    assert chosen == ["model-a"]
    assert missing == ["missing-model"]
    automatic, absent = select_candidates(listed, [], limit=3)
    assert automatic == ["model-a"]
    assert absent == []


def test_listed_model_is_not_usable(db) -> None:
    record_check(db, model_id="model-a", check_name="listed", status="passed")
    assert verified_model_ids(db, "diagnostic") == []


def test_successful_structured_output_is_recorded(db) -> None:
    handler = _capture_logs()
    _verified(db)
    provider = MockProvider(script=[_json_result('{"gap":"chain rule","confidence":"low"}')])
    result, parsed = generate(
        db,
        provider,
        task="diagnostic",
        category="development",
        prompt="PromptSentinel",
        output_model=DiagnosticProbe,
        action_id="act-1",
    )
    assert parsed is not None
    assert parsed.gap == "chain rule"
    assert result.model_id == "model-a"
    usage = db.scalars(select(AiUsageRecord)).one()
    assert usage.status == "succeeded"
    assert usage.input_tokens == 8
    assert Decimal(usage.estimated_cost_usd) > 0
    rendered = "\n".join(handler.lines)
    assert "PromptSentinel" not in rendered
    assert "AIza" not in rendered
    logging.getLogger().removeHandler(handler)


def test_malformed_output_is_rejected(db) -> None:
    _verified(db)
    provider = MockProvider(script=[_json_result("not json")])
    with pytest.raises(AppError) as caught:
        generate(
            db,
            provider,
            task="diagnostic",
            category="development",
            prompt="diagnose",
            output_model=DiagnosticProbe,
        )
    assert caught.value.code == "malformed_output"
    assert db.scalars(select(AiUsageRecord)).one().status == "failed"


def test_timeout_is_retried_once(db) -> None:
    _verified(db)
    provider = MockProvider(
        script=[
            ProviderError("timeout", True),
            _json_result('{"gap":"chain rule","confidence":"high"}'),
        ]
    )
    delays: list[float] = []
    generate(
        db,
        provider,
        task="diagnostic",
        category="development",
        prompt="diagnose",
        output_model=DiagnosticProbe,
        sleeper=delays.append,
    )
    assert len(provider.calls) == 2
    assert delays == [0.25]
    statuses = [row.status for row in db.scalars(select(AiUsageRecord)).all()]
    assert statuses == ["failed", "succeeded"]


@pytest.mark.parametrize("error_class", ["quota", "invalid_key", "model_not_found"])
def test_terminal_provider_errors_are_not_retried(db, error_class: str) -> None:
    _verified(db)
    provider = MockProvider(
        script=[
            ProviderError(error_class, False),
            _json_result('{"gap":"chain rule","confidence":"low"}'),
        ]
    )
    with pytest.raises(AppError) as caught:
        generate(db, provider, task="diagnostic", category="development", prompt="diagnose", output_model=DiagnosticProbe)
    assert caught.value.code == error_class
    assert len(provider.calls) == 1


def test_budget_guard_blocks_before_the_provider_is_called(db) -> None:
    _verified(db)
    record_usage(
        db,
        category="teaching",
        task="seed",
        model_id="model-a",
        status="succeeded",
        estimated_cost_usd=Decimal("19"),
    )
    record_usage(
        db,
        category="evaluation",
        task="seed",
        model_id="model-a",
        status="succeeded",
        estimated_cost_usd=Decimal("1"),
    )
    provider = MockProvider(script=[_json_result('{"gap":"chain rule","confidence":"low"}')])
    with pytest.raises(AppError) as caught:
        generate(db, provider, task="diagnostic", category="demo", prompt="diagnose", output_model=DiagnosticProbe)
    assert caught.value.code == "budget_exceeded"
    assert provider.calls == []


def test_action_call_cap_blocks_a_second_request(db) -> None:
    _verified(db)
    provider = MockProvider(
        script=[
            _json_result('{"gap":"chain rule","confidence":"low"}'),
            _json_result('{"gap":"chain rule","confidence":"low"}'),
        ]
    )
    generate(
        db,
        provider,
        task="diagnostic",
        category="development",
        prompt="diagnose",
        output_model=DiagnosticProbe,
        action_id="same-action",
        max_calls=1,
    )
    with pytest.raises(AppError) as caught:
        generate(
            db,
            provider,
            task="diagnostic",
            category="development",
            prompt="diagnose",
            output_model=DiagnosticProbe,
            action_id="same-action",
            max_calls=1,
        )
    assert caught.value.code == "call_limit"
    assert len(provider.calls) == 1


def test_unverified_model_is_rejected(db) -> None:
    provider = MockProvider(script=[_json_result('{"gap":"chain rule","confidence":"low"}')])
    with pytest.raises(AppError) as caught:
        generate(db, provider, task="diagnostic", category="development", prompt="diagnose", output_model=DiagnosticProbe)
    assert caught.value.code == "model_not_verified"
    assert provider.calls == []


def test_verification_marks_only_a_fully_checked_model(db, tmp_path) -> None:
    provider = MockProvider(
        models=[
            ModelInfo("model-a", ("generateContent",)),
            ModelInfo("text-embedding", ("embedContent",)),
        ],
        script=[
            GenerationResult(text="ready", model_id="model-a", input_tokens=4, output_tokens=1),
            _json_result('{"gap":"chain rule","confidence":"low"}'),
            _json_result(
                '{"explanation":"Use the outer and inner derivative.","check_question":"Differentiate sin of x squared."}'
            ),
            _json_result('{"verdict":"not_met","reason":"The inner derivative is missing."}'),
        ],
    )
    report = tmp_path / "GEMINI_MODEL_STRATEGY.md"
    assert run_verification(db, provider, report, configured=[], limit=3) == 0
    text = report.read_text(encoding="utf-8")
    assert "diagnostic: `model-a`" in text
    assert "teaching: `model-a`" in text
    assert "evaluation: `model-a`" in text
    assert "`text-embedding`" in text
    assert "AIza" not in text
    assert verified_model_ids(db, "teaching") == ["model-a"]


def test_missing_key_is_reported_without_a_model_call(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.ai.verification.get_settings",
        lambda: SimpleNamespace(gemini_api_key=None),
    )
    assert configuration_problem() == "GEMINI_API_KEY is not configured. No model is usable."
