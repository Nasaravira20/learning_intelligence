import json

from app.ai.providers.mock import MockProvider
from app.ai.types import GenerationResult
from app.api.deps import get_model_provider
from app.main import app
from app.pedagogy.schemas import P0_STRATEGY_IDS

PASSWORD = "correct-horse"


def _result(payload: object) -> GenerationResult:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return GenerationResult(text=text, model_id="mock", input_tokens=1, output_tokens=1)


def _ready_session(client, provider, email: str) -> dict:
    account = client.post(
        "/api/auth/signup",
        json={"display_name": "Ada", "email": email, "password": PASSWORD},
    )
    assert account.status_code == 201
    topic = client.post("/api/topics", json={"title": "Backpropagation", "slug": email.split("@")[0], "description": None})
    assert topic.status_code == 201
    objective = client.post(
        f"/api/topics/{topic.json()['id']}/objectives",
        json={
            "code": "chain-rule.apply",
            "statement": "Apply the chain rule.",
            "concept": "chain rule",
            "prerequisite_codes": [],
        },
    )
    assert objective.status_code == 201, objective.text
    session = client.post(
        "/api/sessions",
        json={"learner_id": account.json()["learner_id"], "topic_id": topic.json()["id"]},
    )
    assert session.status_code == 201
    provider.script = [
        _result(
            {
                "questions": [
                    {
                        "objective_code": "chain-rule.apply",
                        "format": "short_answer",
                        "prompt": "Explain chain-rule.apply without a citation.",
                        "choices": None,
                    }
                ]
            }
        ),
        _result(
            {
                "judgments": [
                    {
                        "objective_code": "chain-rule.apply",
                        "answer_verdict": "incorrect",
                        "reasoning_verdict": "weak",
                        "understanding": "none",
                        "confidence": "low",
                        "misconception": None,
                    }
                ]
            }
        ),
    ]
    started = client.post(f"/api/sessions/{session.json()['id']}/diagnosis")
    assert started.status_code == 201, started.text
    submitted = client.post(
        f"/api/sessions/{session.json()['id']}/diagnosis/responses",
        json={
            "responses": [
                {
                    "question_id": started.json()["questions"][0]["id"],
                    "answer_text": "A short answer.",
                    "reasoning_text": "Because the outer function changes.",
                }
            ]
        },
    )
    assert submitted.status_code == 200, submitted.text
    plan = client.post(f"/api/sessions/{session.json()['id']}/plan")
    assert plan.status_code == 201, plan.text
    assert plan.json()["session_status"] == "PLAN_READY"
    return session.json()


def test_selection_persists_without_starting_teaching(client) -> None:
    provider = MockProvider()
    app.dependency_overrides[get_model_provider] = lambda: provider
    try:
        session = _ready_session(client, provider, "ada-select@example.com")
        created = client.post(f"/api/sessions/{session['id']}/pedagogy-selection", json={})
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["session_status"] == "PLAN_READY"
        assert body["controls_teaching"] is False
        assert body["production_primary_strategy"] is None
        assert body["primary_strategy"] in set(P0_STRATEGY_IDS)
        assert body["registry_version"] == "2026.11.21"
        assert body["policy_version"] == "2026.11.21"
        assert body["situation"] == "missing_prerequisites"
        assert "Teaching does not start." in body["rationale"]
        again = client.post(f"/api/sessions/{session['id']}/pedagogy-selection", json={})
        assert again.status_code == 201
        assert again.json()["revision"] == body["revision"]
        assert again.json()["id"] == body["id"]
        loaded = client.get(f"/api/sessions/{session['id']}/pedagogy-selection")
        assert loaded.status_code == 200
        assert loaded.json()["input_fingerprint"] == body["input_fingerprint"]
        session_after = client.get(f"/api/sessions/{session['id']}")
        assert session_after.status_code == 200
        assert session_after.json()["status"] == "PLAN_READY"
    finally:
        app.dependency_overrides.pop(get_model_provider, None)


def test_other_learner_cannot_read_a_selection(client) -> None:
    provider = MockProvider()
    app.dependency_overrides[get_model_provider] = lambda: provider
    try:
        session = _ready_session(client, provider, "ada-private-select@example.com")
        saved = client.post(
            f"/api/sessions/{session['id']}/pedagogy-selection",
            json={
                "context": {
                    "topic": "Backpropagation",
                    "learning_objective": "Understand the chain rule",
                    "learner_level": "partial",
                    "prior_knowledge": ["chain_rule"],
                    "knowledge_gaps": [],
                    "misconceptions": ["confuses_loss_and_gradient"],
                    "recent_performance": [],
                    "session_stage": "practice",
                    "time_available_minutes": 20,
                    "previous_strategy_outcomes": [],
                }
            },
        )
        assert saved.status_code == 201, saved.text
        assert saved.json()["situation"] == "confuses_similar_concepts"
        client.post("/api/auth/signout")
        other = client.post(
            "/api/auth/signup",
            json={"display_name": "Grace", "email": "grace-select@example.com", "password": PASSWORD},
        )
        assert other.status_code == 201
        hidden = client.get(f"/api/sessions/{session['id']}/pedagogy-selection")
        assert hidden.status_code == 404
        assert hidden.json()["error"]["code"] == "session_not_found"
    finally:
        app.dependency_overrides.pop(get_model_provider, None)


def test_selection_waits_for_a_plan(client) -> None:
    account = client.post(
        "/api/auth/signup",
        json={"display_name": "Ada", "email": "ada-early-select@example.com", "password": PASSWORD},
    )
    topic = client.post("/api/topics", json={"title": "Backpropagation", "slug": "early-select", "description": None})
    session = client.post(
        "/api/sessions",
        json={"learner_id": account.json()["learner_id"], "topic_id": topic.json()["id"]},
    )
    early = client.post(f"/api/sessions/{session.json()['id']}/pedagogy-selection", json={})
    assert early.status_code == 409
    assert early.json()["error"]["code"] == "selection_not_ready"
