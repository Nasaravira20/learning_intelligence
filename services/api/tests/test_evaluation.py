import json

from app.ai.providers.mock import MockProvider
from app.ai.types import GenerationResult
from app.api.deps import get_model_provider
from app.main import app
from tests.test_teaching import HIDDEN, _planned_session

PASSWORD = "correct-horse"


def _result(payload: object) -> GenerationResult:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return GenerationResult(text=text, model_id="mock", input_tokens=1, output_tokens=1)


def _judgment(**overrides) -> dict:
    payload = {
        "objective_code": "chain-rule.apply",
        "answer_verdict": "correct",
        "reasoning_verdict": "sound",
        "understanding": "solid",
        "confidence": "high",
        "misconception": None,
    }
    payload.update(overrides)
    return payload


def _taught(client, email: str) -> str:
    session = _planned_session(client, email)
    started = client.post(f"/api/sessions/{session['id']}/teaching")
    assert started.status_code == 201, started.text
    return session["id"]


def test_weak_reasoning_keeps_full_credit_and_asks_again(client) -> None:
    session_id = _taught(client, "eval-weak@example.com")
    opened = client.post(f"/api/sessions/{session_id}/evaluation")
    assert opened.status_code == 201, opened.text
    assert opened.json()["session_status"] == "EVALUATING"
    assert "chain-rule.apply" in opened.json()["prompt"]
    submitted = client.post(
        f"/api/sessions/{session_id}/evaluation/response",
        json={"answer_text": HIDDEN, "reasoning_text": "This is a weak reason."},
    )
    assert submitted.status_code == 200, submitted.text
    body = submitted.json()
    assert body["decision"] == "further_assessment"
    assert body["credit"] == "1.000"
    assert body["session_status"] == "EVALUATING"
    assert body["status"] == "completed"
    again = client.post(f"/api/sessions/{session_id}/evaluation")
    assert again.status_code == 201, again.text
    assert again.json()["revision"] == 2
    assert again.json()["status"] == "open"
    assert again.json()["decision"] is None


def test_partial_credit_changes_strategy_and_can_be_reassessed(client) -> None:
    session_id = _taught(client, "eval-partial@example.com")
    assert client.post(f"/api/sessions/{session_id}/evaluation").status_code == 201
    submitted = client.post(
        f"/api/sessions/{session_id}/evaluation/response",
        json={"answer_text": "A partial outer step only", "reasoning_text": "I stopped halfway."},
    )
    body = submitted.json()
    assert submitted.status_code == 200, submitted.text
    assert body["decision"] == "remediation"
    assert body["credit"] == "0.500"
    assert body["session_status"] == "REMEDIATION"
    assert "Partial credit" in body["feedback"]
    assert body["remediation_strategy"] == "concrete_examples"
    changed = client.post(f"/api/sessions/{session_id}/evaluation/remediation")
    assert changed.status_code == 200, changed.text
    assert changed.json()["session_status"] == "TEACHING"
    lesson = client.get(f"/api/sessions/{session_id}/teaching")
    assert lesson.status_code == 200
    strategies = {item["strategy_id"] for item in lesson.json()["activities"]}
    assert "concrete_examples" in strategies
    check = client.post(f"/api/sessions/{session_id}/evaluation")
    assert check.status_code == 201, check.text
    assert check.json()["session_status"] == "EVALUATING"
    assert check.json()["revision"] == 2


def test_uncertain_judgment_needs_review_without_observed_knowledge(client) -> None:
    session_id = _taught(client, "eval-review@example.com")
    assert client.post(f"/api/sessions/{session_id}/evaluation").status_code == 201
    submitted = client.post(
        f"/api/sessions/{session_id}/evaluation/response",
        json={"answer_text": "I am not sure", "reasoning_text": "I am not sure either"},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["decision"] == "needs_review"
    assert submitted.json()["session_status"] == "NEEDS_REVIEW"
    knowledge = client.get("/api/learner/knowledge")
    observed = [item for item in knowledge.json() if item["concept"] == "chain rule" and item["evidence_kind"] == "observed"]
    assert observed == []


def test_strong_evidence_records_mastery_and_closes_the_check(client) -> None:
    session_id = _taught(client, "eval-master@example.com")
    assert client.post(f"/api/sessions/{session_id}/evaluation").status_code == 201
    provider = MockProvider(script=[_result(_judgment())])
    app.dependency_overrides[get_model_provider] = lambda: provider
    try:
        submitted = client.post(
            f"/api/sessions/{session_id}/evaluation/response",
            json={"answer_text": HIDDEN, "reasoning_text": "Inner change, then outer change."},
        )
    finally:
        app.dependency_overrides.pop(get_model_provider, None)
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["decision"] == "mastered"
    assert submitted.json()["credit"] == "1.000"
    assert submitted.json()["session_status"] == "MASTERED"
    knowledge = client.get("/api/learner/knowledge")
    mastered = [item for item in knowledge.json() if item["concept"] == "chain rule"]
    assert mastered[0]["evidence_kind"] == "observed"
    assert mastered[0]["confirmed"] is True
    closed = client.post(f"/api/sessions/{session_id}/evaluation")
    assert closed.status_code == 409
    assert closed.json()["error"]["code"] == "evaluation_closed"


def test_misconception_evidence_is_copied_from_the_answer(client) -> None:
    session_id = _taught(client, "eval-copy@example.com")
    assert client.post(f"/api/sessions/{session_id}/evaluation").status_code == 201
    phrase = "I mixed the outer step only"
    provider = MockProvider(
        script=[
            _result(
                _judgment(
                    answer_verdict="partial",
                    reasoning_verdict="partial",
                    understanding="partial",
                    confidence="medium",
                    misconception={
                        "concept": "chain rule",
                        "description": "The outer step was treated as the whole derivative.",
                        "evidence": phrase,
                        "confidence": "medium",
                    },
                )
            )
        ]
    )
    app.dependency_overrides[get_model_provider] = lambda: provider
    try:
        submitted = client.post(
            f"/api/sessions/{session_id}/evaluation/response",
            json={"answer_text": phrase, "reasoning_text": "The rest was missing."},
        )
    finally:
        app.dependency_overrides.pop(get_model_provider, None)
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["misconception_evidence"] == phrase
    assert submitted.json()["session_status"] != "MASTERED"
    session_id = _taught(client, "eval-evidence@example.com")
    assert client.post(f"/api/sessions/{session_id}/evaluation").status_code == 201
    provider = MockProvider(
        script=[
            _result(
                _judgment(
                    misconception={
                        "concept": "chain rule",
                        "description": "The outer step was treated as the whole derivative.",
                        "evidence": "a phrase the learner never wrote",
                        "confidence": "medium",
                    }
                )
            )
        ]
    )
    app.dependency_overrides[get_model_provider] = lambda: provider
    try:
        rejected = client.post(
            f"/api/sessions/{session_id}/evaluation/response",
            json={"answer_text": "I mixed the outer step only", "reasoning_text": "The rest was missing."},
        )
    finally:
        app.dependency_overrides.pop(get_model_provider, None)
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "malformed_output"
    saved = client.get(f"/api/sessions/{session_id}/evaluation")
    assert saved.json()["status"] == "open"
    assert saved.json()["session_status"] == "EVALUATING"


def test_evaluation_is_private_and_waits_for_a_lesson(client) -> None:
    account = client.post(
        "/api/auth/signup",
        json={"display_name": "Ada", "email": "eval-early@example.com", "password": PASSWORD},
    )
    topic = client.post("/api/topics", json={"title": "Early", "slug": "eval-early", "description": None})
    created = client.post(
        "/api/sessions",
        json={"learner_id": account.json()["learner_id"], "topic_id": topic.json()["id"]},
    )
    early = client.post(f"/api/sessions/{created.json()['id']}/evaluation")
    assert early.status_code == 409
    assert early.json()["error"]["code"] == "evaluation_not_ready"
    session_id = _taught(client, "eval-owner@example.com")
    assert client.post(f"/api/sessions/{session_id}/evaluation").status_code == 201
    client.post("/api/auth/signout")
    other = client.post(
        "/api/auth/signup",
        json={"display_name": "Bea", "email": "eval-other@example.com", "password": PASSWORD},
    )
    assert other.status_code == 201
    hidden = client.get(f"/api/sessions/{session_id}/evaluation")
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "session_not_found"
