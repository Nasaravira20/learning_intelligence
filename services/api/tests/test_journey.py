import json
from datetime import datetime, timedelta, timezone
from time import perf_counter

from app.ai.providers.mock import MockProvider
from app.ai.types import GenerationResult
from app.api.deps import get_model_provider
from app.main import app
from app.retention import policy as retention_policy

PASSWORD = "correct-horse"
UTC = timezone.utc


def _result(payload: object) -> GenerationResult:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return GenerationResult(text=text, model_id="mock", input_tokens=1, output_tokens=1)


def _mastery() -> dict:
    return {
        "objective_code": "derivatives.basic",
        "answer_verdict": "correct",
        "reasoning_verdict": "sound",
        "understanding": "solid",
        "confidence": "high",
        "misconception": None,
    }


def test_a_new_learner_can_finish_the_loop_and_delete_the_account(client, monkeypatch) -> None:
    started_at = perf_counter()
    learned = datetime(2026, 11, 21, 15, 0, tzinfo=UTC)
    monkeypatch.setattr(retention_policy, "current_time", lambda: learned)
    account = client.post(
        "/api/auth/signup",
        json={"display_name": "Ada", "email": "journey@example.com", "password": PASSWORD},
    )
    assert account.status_code == 201
    topic = client.post(
        "/api/topics",
        json={"title": "Backpropagation", "slug": "journey-backprop", "description": None},
    )
    topic_id = topic.json()["id"]
    first = client.post(
        f"/api/topics/{topic_id}/objectives",
        json={
            "code": "derivatives.basic",
            "statement": "Show a basic derivative.",
            "concept": "derivatives",
            "prerequisite_codes": [],
        },
    )
    assert first.status_code == 201
    second = client.post(
        f"/api/topics/{topic_id}/objectives",
        json={
            "code": "chain-rule.apply",
            "statement": "Apply the chain rule.",
            "concept": "chain rule",
            "prerequisite_codes": ["derivatives.basic"],
        },
    )
    assert second.status_code == 201, second.text
    created = client.post(
        "/api/sessions",
        json={"learner_id": account.json()["learner_id"], "topic_id": topic_id},
    )
    session_id = created.json()["id"]
    started = client.post(f"/api/sessions/{session_id}/diagnosis")
    assert started.status_code == 201, started.text
    submitted = client.post(
        f"/api/sessions/{session_id}/diagnosis/responses",
        json={
            "responses": [
                {
                    "question_id": item["id"],
                    "answer_text": "A short answer.",
                    "reasoning_text": "Because the outer function changes.",
                }
                for item in started.json()["questions"]
            ]
        },
    )
    assert submitted.status_code == 200, submitted.text
    plan = client.post(f"/api/sessions/{session_id}/plan")
    assert plan.status_code == 201, plan.text
    assert plan.json()["starting_objective_code"] == "derivatives.basic"
    selection = client.post(f"/api/sessions/{session_id}/pedagogy-selection", json={})
    assert selection.status_code == 201, selection.text
    assert selection.json()["primary_strategy"] == "small_step_instruction"
    lesson = client.post(f"/api/sessions/{session_id}/teaching")
    assert lesson.status_code == 201, lesson.text
    assert "small_step_instruction" in {item["strategy_id"] for item in lesson.json()["activities"]}
    resumed = client.post(f"/api/sessions/{session_id}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "TEACHING"
    assert client.get(f"/api/sessions/{session_id}/teaching").status_code == 200
    opened = client.post(f"/api/sessions/{session_id}/evaluation")
    assert opened.status_code == 201, opened.text
    partial = client.post(
        f"/api/sessions/{session_id}/evaluation/response",
        json={"answer_text": "A partial outer step only", "reasoning_text": "I stopped halfway."},
    )
    assert partial.status_code == 200, partial.text
    assert partial.json()["decision"] == "remediation"
    assert partial.json()["session_status"] == "REMEDIATION"
    changed = client.post(f"/api/sessions/{session_id}/evaluation/remediation")
    assert changed.status_code == 200, changed.text
    strategies = {item["strategy_id"] for item in client.get(f"/api/sessions/{session_id}/teaching").json()["activities"]}
    assert "concrete_examples" in strategies
    assert client.post(f"/api/sessions/{session_id}/evaluation").status_code == 201
    provider = MockProvider(script=[_result(_mastery())])
    app.dependency_overrides[get_model_provider] = lambda: provider
    try:
        mastered = client.post(
            f"/api/sessions/{session_id}/evaluation/response",
            json={"answer_text": "The rate of the outer change.", "reasoning_text": "The inner change comes first."},
        )
    finally:
        app.dependency_overrides.pop(get_model_provider, None)
    assert mastered.status_code == 200, mastered.text
    assert mastered.json()["session_status"] == "MASTERED"
    monkeypatch.setattr(retention_policy, "current_time", lambda: learned + timedelta(days=1))
    review = client.post(f"/api/sessions/{session_id}/retention")
    assert review.status_code == 201, review.text
    assert "derivatives.basic" in review.json()["prompt"]
    provider = MockProvider(script=[_result(_mastery())])
    app.dependency_overrides[get_model_provider] = lambda: provider
    try:
        recalled = client.post(
            f"/api/sessions/{session_id}/retention/response",
            json={"answer_text": "The rate of the outer change.", "reasoning_text": "The inner change comes first."},
        )
    finally:
        app.dependency_overrides.pop(get_model_provider, None)
    assert recalled.status_code == 200, recalled.text
    assert recalled.json()["session_status"] == "MASTERY_UPDATED"
    saved = client.get(f"/api/sessions/{session_id}/retention")
    assert saved.status_code == 200
    assert saved.json()["mastery"][-1]["evidence_kind"] == "observed"
    knowledge = client.get("/api/learner/knowledge")
    assert any(item["concept"] == "derivatives" and item["evidence_kind"] == "observed" for item in knowledge.json())
    client.post("/api/auth/signout")
    other = client.post(
        "/api/auth/signup",
        json={"display_name": "Bea", "email": "journey-other@example.com", "password": PASSWORD},
    )
    assert other.status_code == 201
    hidden = client.get(f"/api/sessions/{session_id}")
    assert hidden.status_code == 404
    client.post("/api/auth/signout")
    again = client.post(
        "/api/auth/signin",
        json={"email": "journey@example.com", "password": PASSWORD},
    )
    assert again.status_code == 200
    removed = client.delete("/api/auth/account")
    assert removed.status_code == 200
    assert removed.json()["status"] == "deleted"
    assert client.get("/api/auth/me").status_code == 401
    refused = client.post(
        "/api/auth/signin",
        json={"email": "journey@example.com", "password": PASSWORD},
    )
    assert refused.status_code == 401
    reused = client.post(
        "/api/auth/signup",
        json={"display_name": "Ada", "email": "journey@example.com", "password": PASSWORD},
    )
    assert reused.status_code == 201
    assert client.get("/api/learner/knowledge").json() == []
    assert perf_counter() - started_at < 60
