import json
import logging
from uuid import UUID

import pytest
from sqlalchemy import select

from app.ai.providers.mock import MockProvider
from app.ai.types import GenerationResult
from app.core.errors import AppError
from app.main import app
from app.api.deps import get_model_provider

PASSWORD = "correct-horse"
SECRET_ANSWER = "PromptShouldNotBeLoggedXYZ"


class CollectHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(self.format(record))


def _capture_logs():
    from app.core.logging import JsonFormatter, RequestIdFilter

    handler = CollectHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())
    logging.getLogger().addHandler(handler)
    return handler


def _signup(client, name: str, email: str) -> dict:
    response = client.post(
        "/api/auth/signup",
        json={"display_name": name, "email": email, "password": PASSWORD},
    )
    assert response.status_code == 201
    return response.json()


def _topic(client, title: str, slug: str) -> dict:
    response = client.post("/api/topics", json={"title": title, "slug": slug, "description": None})
    assert response.status_code == 201
    return response.json()


def _objective(client, topic_id: str, code: str, concept: str, prerequisites: list[str] | None = None) -> dict:
    response = client.post(
        f"/api/topics/{topic_id}/objectives",
        json={
            "code": code,
            "statement": f"Show understanding of {concept}.",
            "concept": concept,
            "prerequisite_codes": prerequisites or [],
        },
    )
    assert response.status_code == 201
    return response.json()


def _session(client, learner_id: str, topic_id: str) -> dict:
    response = client.post("/api/sessions", json={"learner_id": learner_id, "topic_id": topic_id})
    assert response.status_code == 201
    return response.json()


def _result(payload: object) -> GenerationResult:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return GenerationResult(text=text, model_id="mock", input_tokens=1, output_tokens=1)


def _questions(codes: list[str]) -> dict:
    formats = ["short_answer", "multiple_choice", "reasoning"]
    questions = []
    for index, code in enumerate(codes):
        question_format = formats[index % len(formats)]
        questions.append(
            {
                "objective_code": code,
                "format": question_format,
                "prompt": f"Explain {code} without a citation.",
                "choices": ["First option", "Second option"] if question_format == "multiple_choice" else None,
            }
        )
    return {"questions": questions}


@pytest.fixture
def provider(client):
    scripted = MockProvider()
    app.dependency_overrides[get_model_provider] = lambda: scripted
    yield scripted
    app.dependency_overrides.pop(get_model_provider, None)


def test_diagnosis_requires_objectives_and_rejects_unknown_prerequisites(client, provider) -> None:
    del provider
    account = _signup(client, "Ada", "ada-objectives@example.com")
    topic = _topic(client, "Chain rule", "chain-rule-objectives")
    session = _session(client, account["learner_id"], topic["id"])
    missing = client.post(f"/api/sessions/{session['id']}/diagnosis")
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "objectives_required"
    unknown = client.post(
        f"/api/topics/{topic['id']}/objectives",
        json={
            "code": "chain-rule.apply",
            "statement": "Differentiate a composition.",
            "concept": "chain rule",
            "prerequisite_codes": ["functions.basic"],
        },
    )
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "prerequisite_not_found"


def test_questions_align_with_objectives_and_results_persist(client, provider) -> None:
    account = _signup(client, "Ada", "ada-align@example.com")
    topic = _topic(client, "Chain rule", "chain-rule-align")
    _objective(client, topic["id"], "functions.basic", "functions")
    _objective(client, topic["id"], "chain-rule.apply", "chain rule", ["functions.basic"])
    session = _session(client, account["learner_id"], topic["id"])
    provider.script = [
        _result(_questions(["functions.basic", "chain-rule.apply"])),
        _result(
            {
                "judgments": [
                    {
                        "objective_code": "functions.basic",
                        "answer_verdict": "incorrect",
                        "reasoning_verdict": "weak",
                        "understanding": "none",
                        "confidence": "medium",
                        "misconception": None,
                    },
                    {
                        "objective_code": "chain-rule.apply",
                        "answer_verdict": "partial",
                        "reasoning_verdict": "partial",
                        "understanding": "partial",
                        "confidence": "medium",
                        "misconception": None,
                    },
                ]
            }
        ),
    ]
    started = client.post(f"/api/sessions/{session['id']}/diagnosis")
    assert started.status_code == 201
    body = started.json()
    assert body["session_status"] == "DIAGNOSING"
    assert {item["objective_code"] for item in body["questions"]} == {"functions.basic", "chain-rule.apply"}
    assert {item["format"] for item in body["questions"]} == {"short_answer", "multiple_choice"}
    assert "functions.basic" in provider.calls[0].prompt
    assert "chain-rule.apply" in provider.calls[0].prompt
    responses = client.post(
        f"/api/sessions/{session['id']}/diagnosis/responses",
        json={
            "responses": [
                {"question_id": item["id"], "answer_text": "A short answer.", "reasoning_text": "Because the outer function changes."}
                for item in body["questions"]
            ]
        },
    )
    assert responses.status_code == 200
    completed = responses.json()
    assert completed["status"] == "completed"
    assert completed["starting_point"] == "beginner"
    assert completed["first_unmet_objective_code"] == "functions.basic"
    chain = next(item for item in completed["judgments"] if item["objective_code"] == "chain-rule.apply")
    assert chain["answer_verdict"] == "partial"
    assert chain["reasoning_verdict"] == "partial"
    assert chain["understanding"] == "partial"
    assert chain["confirmed"] is False
    again = client.get(f"/api/sessions/{session['id']}/diagnosis")
    assert again.status_code == 200
    assert again.json()["id"] == completed["id"]
    assert again.json()["summary"] == completed["summary"]

    from app.db.session import get_sessionmaker
    from app.models import DiagnosticAttempt

    fresh = get_sessionmaker()()
    try:
        stored = fresh.scalar(select(DiagnosticAttempt).where(DiagnosticAttempt.id == UUID(completed["id"])))
        assert stored is not None
        assert stored.starting_point == "beginner"
        assert stored.status == "completed"
    finally:
        fresh.close()


def test_invalid_model_output_is_rejected_without_saving_a_diagnosis(client, provider) -> None:
    account = _signup(client, "Ada", "ada-invalid@example.com")
    topic = _topic(client, "Chain rule", "chain-rule-invalid")
    _objective(client, topic["id"], "functions.basic", "functions")
    session = _session(client, account["learner_id"], topic["id"])
    provider.script = [_result("not json")]
    rejected = client.post(f"/api/sessions/{session['id']}/diagnosis")
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "malformed_output"
    assert client.get(f"/api/sessions/{session['id']}/diagnosis").status_code == 404
    listed = client.get(f"/api/sessions/{session['id']}")
    assert listed.json()["status"] == "TOPIC_SELECTED"

    provider.script = [_result(_questions(["invented.code"]))]
    invented = client.post(f"/api/sessions/{session['id']}/diagnosis")
    assert invented.status_code == 422
    assert invented.json()["error"]["code"] == "malformed_output"
    assert client.get(f"/api/sessions/{session['id']}").json()["status"] == "TOPIC_SELECTED"


def test_a_fabricated_quote_does_not_create_a_misconception(client, provider) -> None:
    account = _signup(client, "Ada", "ada-quote@example.com")
    topic = _topic(client, "Chain rule", "chain-rule-quote")
    _objective(client, topic["id"], "loss.gradient", "loss")
    session = _session(client, account["learner_id"], topic["id"])
    provider.script = [
        _result(_questions(["loss.gradient"])),
        _result(
            {
                "judgments": [
                    {
                        "objective_code": "loss.gradient",
                        "answer_verdict": "incorrect",
                        "reasoning_verdict": "weak",
                        "understanding": "none",
                        "confidence": "medium",
                        "misconception": {
                            "concept": "loss",
                            "description": "Loss and gradient were treated as the same thing.",
                            "evidence": "This quotation was not written by the learner.",
                            "confidence": "low",
                        },
                    }
                ]
            }
        ),
    ]
    started = client.post(f"/api/sessions/{session['id']}/diagnosis")
    assert started.status_code == 201
    question_id = started.json()["questions"][0]["id"]
    handler = _capture_logs()
    try:
        submitted = client.post(
            f"/api/sessions/{session['id']}/diagnosis/responses",
            json={"responses": [{"question_id": question_id, "answer_text": SECRET_ANSWER, "reasoning_text": "I am not sure."}]},
        )
    finally:
        logging.getLogger().removeHandler(handler)
    assert submitted.status_code == 422
    assert submitted.json()["error"]["code"] == "malformed_output"
    assert SECRET_ANSWER not in "\n".join(handler.lines)
    report = client.get(f"/api/sessions/{session['id']}/diagnosis")
    assert report.status_code == 200
    assert report.json()["status"] == "in_progress"
    assert report.json()["judgments"] == []
    assert report.json()["misconceptions"] == []
    dashboard = client.get("/api/learner")
    assert dashboard.json()["misconceptions"] == []


def test_other_learner_cannot_read_a_diagnosis(client, provider) -> None:
    del provider
    ada = _signup(client, "Ada", "ada-private-diagnosis@example.com")
    topic = _topic(client, "Chain rule", "chain-rule-private-diagnosis")
    session = _session(client, ada["learner_id"], topic["id"])
    client.cookies.clear()
    _signup(client, "Grace", "grace-private-diagnosis@example.com")
    hidden = client.get(f"/api/sessions/{session['id']}/diagnosis")
    assert hidden.status_code == 404
    started = client.post(f"/api/sessions/{session['id']}/diagnosis")
    assert started.status_code == 404


def test_invalid_session_transition_is_rejected(client, provider) -> None:
    del provider
    account = _signup(client, "Ada", "ada-transition@example.com")
    topic = _topic(client, "Chain rule", "chain-rule-transition")
    created = _session(client, account["learner_id"], topic["id"])
    from app.db.session import get_sessionmaker
    from app.models import LearningSession
    from app.services.sessions import enter_diagnosis

    db = get_sessionmaker()()
    try:
        item = db.get(LearningSession, UUID(created["id"]))
        assert item is not None
        item.status = "TEACHING"
        with pytest.raises(AppError) as caught:
            enter_diagnosis(db, item)
        assert caught.value.code == "invalid_transition"
    finally:
        db.rollback()
        db.close()


def test_development_provider_keeps_questions_on_the_defined_objectives(client) -> None:
    account = _signup(client, "Ada", "ada-mock@example.com")
    topic = _topic(client, "Chain rule", "chain-rule-mock")
    _objective(client, topic["id"], "functions.basic", "functions")
    _objective(client, topic["id"], "derivatives.basic", "derivatives", ["functions.basic"])
    session = _session(client, account["learner_id"], topic["id"])
    started = client.post(f"/api/sessions/{session['id']}/diagnosis")
    assert started.status_code == 201
    questions = started.json()["questions"]
    assert {item["objective_code"] for item in questions} == {"functions.basic", "derivatives.basic"}
    assert len({item["format"] for item in questions}) == 2
