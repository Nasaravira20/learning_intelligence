import json
from datetime import datetime, timedelta, timezone

from app.ai.providers.mock import MockProvider
from app.ai.types import GenerationResult
from app.api.deps import get_model_provider
from app.main import app
from app.retention import policy as retention_policy
from tests.test_evaluation import _judgment, _taught

UTC = timezone.utc
PASSWORD = "correct-horse"


def _result(payload: object) -> GenerationResult:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return GenerationResult(text=text, model_id="mock", input_tokens=1, output_tokens=1)


def _mastered(client, email: str, when: datetime) -> str:
    session_id = _taught(client, email)
    assert client.post(f"/api/sessions/{session_id}/evaluation").status_code == 201
    provider = MockProvider(script=[_result(_judgment())])
    app.dependency_overrides[get_model_provider] = lambda: provider
    try:
        submitted = client.post(
            f"/api/sessions/{session_id}/evaluation/response",
            json={"answer_text": "Inner then outer.", "reasoning_text": "The inner change is applied first."},
        )
    finally:
        app.dependency_overrides.pop(get_model_provider, None)
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["session_status"] == "MASTERED"
    return session_id


def test_a_mastered_objective_is_due_on_the_next_local_day_and_can_be_recalled(client, monkeypatch) -> None:
    learned = datetime(2026, 11, 21, 15, 0, tzinfo=UTC)
    monkeypatch.setattr(retention_policy, "current_time", lambda: learned)
    session_id = _mastered(client, "retain-due@example.com", learned)
    listed = client.get("/api/retention")
    assert listed.status_code == 200, listed.text
    review = listed.json()[0]
    assert review["due_on"] == "2026-11-22"
    assert review["timing"] == "scheduled"
    assert review["interval_index"] == 0
    early = client.post(f"/api/sessions/{session_id}/retention")
    assert early.status_code == 409
    assert early.json()["error"]["code"] == "retention_not_due"
    monkeypatch.setattr(retention_policy, "current_time", lambda: learned + timedelta(days=1))
    due = client.get("/api/retention")
    assert due.json()[0]["timing"] == "due"
    started = client.post(f"/api/sessions/{session_id}/retention")
    assert started.status_code == 201, started.text
    assert started.json()["session_status"] == "RETENTION_ASSESSMENT"
    assert "chain-rule.apply" in started.json()["prompt"]
    assert "Recall" in started.json()["prompt"]
    assert "answer is shown" in started.json()["prompt"]
    provider = MockProvider(script=[_result(_judgment())])
    app.dependency_overrides[get_model_provider] = lambda: provider
    try:
        recalled = client.post(
            f"/api/sessions/{session_id}/retention/response",
            json={"answer_text": "Inner then outer.", "reasoning_text": "The same reason still holds."},
        )
    finally:
        app.dependency_overrides.pop(get_model_provider, None)
    assert recalled.status_code == 200, recalled.text
    assert recalled.json()["outcome"] == "recalled"
    assert recalled.json()["session_status"] == "MASTERY_UPDATED"
    saved = client.get(f"/api/sessions/{session_id}/retention")
    body = saved.json()
    assert [item["status"] for item in body["reviews"]] == ["completed", "scheduled"]
    assert body["reviews"][1]["due_on"] == "2026-11-25"
    assert body["reviews"][1]["interval_index"] == 1
    assert body["mastery"][-1]["decision"] == "mastered"
    assert body["mastery"][-1]["evidence_kind"] == "observed"
    assert body["mastery"][-1]["credit"] == "1.000"
    assert len(body["mastery"]) >= 2


def test_a_missed_review_resets_the_interval_after_recall(client, monkeypatch) -> None:
    learned = datetime(2026, 11, 21, 15, 0, tzinfo=UTC)
    monkeypatch.setattr(retention_policy, "current_time", lambda: learned)
    session_id = _mastered(client, "retain-miss@example.com", learned)
    monkeypatch.setattr(retention_policy, "current_time", lambda: learned + timedelta(days=2))
    assert client.get("/api/retention").json()[0]["timing"] == "missed"
    started = client.post(f"/api/sessions/{session_id}/retention")
    assert started.status_code == 201, started.text
    assert started.json()["was_missed"] is True
    provider = MockProvider(script=[_result(_judgment())])
    app.dependency_overrides[get_model_provider] = lambda: provider
    try:
        recalled = client.post(
            f"/api/sessions/{session_id}/retention/response",
            json={"answer_text": "Inner then outer.", "reasoning_text": "The same reason still holds."},
        )
    finally:
        app.dependency_overrides.pop(get_model_provider, None)
    assert recalled.status_code == 200, recalled.text
    saved = client.get(f"/api/sessions/{session_id}/retention").json()
    upcoming = saved["reviews"][-1]
    assert upcoming["interval_index"] == 0
    assert upcoming["due_on"] == "2026-11-24"


def test_a_failed_recall_returns_to_remediation_with_a_short_next_review(client, monkeypatch) -> None:
    learned = datetime(2026, 11, 21, 15, 0, tzinfo=UTC)
    monkeypatch.setattr(retention_policy, "current_time", lambda: learned)
    session_id = _mastered(client, "retain-fail@example.com", learned)
    monkeypatch.setattr(retention_policy, "current_time", lambda: learned + timedelta(days=1))
    assert client.post(f"/api/sessions/{session_id}/retention").status_code == 201
    failed = client.post(
        f"/api/sessions/{session_id}/retention/response",
        json={"answer_text": "A partial outer step only", "reasoning_text": "I stopped halfway."},
    )
    assert failed.status_code == 200, failed.text
    assert failed.json()["outcome"] == "failed"
    assert failed.json()["session_status"] == "REMEDIATION"
    saved = client.get(f"/api/sessions/{session_id}/retention").json()
    assert saved["mastery"][-1]["decision"] == "remediation"
    assert saved["mastery"][-1]["evidence_kind"] == "inferred"
    assert saved["reviews"][-1]["interval_index"] == 0
    assert saved["reviews"][-1]["due_on"] == "2026-11-23"
    blocked = client.post(f"/api/sessions/{session_id}/retention")
    assert blocked.status_code == 409
    taught = client.post(f"/api/sessions/{session_id}/evaluation/remediation")
    assert taught.status_code == 200, taught.text
    assert taught.json()["session_status"] == "TEACHING"
    lesson = client.get(f"/api/sessions/{session_id}/teaching")
    strategies = {item["strategy_id"] for item in lesson.json()["activities"]}
    assert "concrete_examples" in strategies
    assert "small_step_instruction" not in strategies


def test_a_review_can_be_resumed_and_stays_private(client, monkeypatch) -> None:
    learned = datetime(2026, 11, 21, 15, 0, tzinfo=UTC)
    monkeypatch.setattr(retention_policy, "current_time", lambda: learned)
    session_id = _mastered(client, "retain-resume@example.com", learned)
    monkeypatch.setattr(retention_policy, "current_time", lambda: learned + timedelta(days=1))
    assert client.post(f"/api/sessions/{session_id}/retention").status_code == 201
    resumed = client.post(f"/api/sessions/{session_id}/resume")
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["status"] == "RETENTION_ASSESSMENT"
    assert resumed.json()["resumed_at"] is not None
    saved = client.get(f"/api/sessions/{session_id}/retention")
    assert saved.json()["reviews"][-1]["status"] == "in_progress"
    client.post("/api/auth/signout")
    other = client.post(
        "/api/auth/signup",
        json={"display_name": "Bea", "email": "retain-other@example.com", "password": PASSWORD},
    )
    assert other.status_code == 201
    hidden = client.get(f"/api/sessions/{session_id}/retention")
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "session_not_found"
    assert client.get("/api/retention").json() == []
    early = _taught(client, "retain-early@example.com")
    blocked = client.post(f"/api/sessions/{early}/retention")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "retention_not_ready"
