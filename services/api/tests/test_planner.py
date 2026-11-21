import json
from uuid import UUID

import pytest

from app.ai.providers.mock import MockProvider
from app.ai.types import GenerationResult
from app.api.deps import get_model_provider
from app.main import app

PASSWORD = "correct-horse"


def _signup(client, name: str, email: str) -> dict:
    response = client.post("/api/auth/signup", json={"display_name": name, "email": email, "password": PASSWORD})
    assert response.status_code == 201
    return response.json()


def _topic(client, title: str, slug: str) -> dict:
    response = client.post("/api/topics", json={"title": title, "slug": slug, "description": None})
    assert response.status_code == 201
    return response.json()


def _objective(
    client,
    topic_id: str,
    code: str,
    concept: str,
    statement: str,
    prerequisites: list[str] | None = None,
) -> dict:
    response = client.post(
        f"/api/topics/{topic_id}/objectives",
        json={
            "code": code,
            "statement": statement,
            "concept": concept,
            "prerequisite_codes": prerequisites or [],
        },
    )
    assert response.status_code == 201, response.text
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


def _met(code: str) -> dict:
    return {
        "objective_code": code,
        "answer_verdict": "correct",
        "reasoning_verdict": "sound",
        "understanding": "solid",
        "confidence": "high",
        "misconception": None,
    }


def _open(code: str, understanding: str = "none", answer: str = "incorrect", reasoning: str = "weak") -> dict:
    return {
        "objective_code": code,
        "answer_verdict": answer,
        "reasoning_verdict": reasoning,
        "understanding": understanding,
        "confidence": "medium",
        "misconception": None,
    }


def _graph(client, topic_id: str) -> None:
    _objective(client, topic_id, "derivatives.basic", "derivatives", "Show a basic derivative.")
    backprop = _objective(
        client,
        topic_id,
        "backprop.step",
        "backpropagation",
        "Apply one backpropagation step.",
        ["derivatives.basic"],
    )
    _objective(
        client,
        topic_id,
        "chain-rule.apply",
        "chain rule",
        "Apply the chain rule.",
        ["derivatives.basic"],
    )
    linked = client.post(
        f"/api/topics/{topic_id}/objectives/{backprop['id']}/prerequisites",
        json={"prerequisite_code": "chain-rule.apply"},
    )
    assert linked.status_code == 200
    assert linked.json()["prerequisite_codes"] == ["derivatives.basic", "chain-rule.apply"]


def _answer(client, provider, session_id: str, codes: list[str], judgments: list[dict], path: str) -> dict:
    provider.script = [_result(_questions(codes)), _result({"judgments": judgments})]
    started = client.post(path)
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
    return submitted.json()


def _diagnose(client, provider, session_id: str, codes: list[str], judgments: list[dict]) -> dict:
    return _answer(client, provider, session_id, codes, judgments, f"/api/sessions/{session_id}/diagnosis")


def _follow_up(client, provider, session_id: str, codes: list[str], judgments: list[dict]) -> dict:
    return _answer(client, provider, session_id, codes, judgments, f"/api/sessions/{session_id}/diagnosis/follow-up")


@pytest.fixture
def provider(client):
    scripted = MockProvider()
    app.dependency_overrides[get_model_provider] = lambda: scripted
    yield scripted
    app.dependency_overrides.pop(get_model_provider, None)


def test_dependency_cycle_is_rejected(client, provider) -> None:
    del provider
    _signup(client, "Ada", "ada-cycle@example.com")
    topic = _topic(client, "Backpropagation", "cycle-plan")
    first = _objective(client, topic["id"], "chain-rule.apply", "chain rule", "Apply the chain rule.")
    _objective(
        client,
        topic["id"],
        "backprop.step",
        "backpropagation",
        "Apply one backpropagation step.",
        ["chain-rule.apply"],
    )
    cycle = client.post(
        f"/api/topics/{topic['id']}/objectives/{first['id']}/prerequisites",
        json={"prerequisite_code": "backprop.step"},
    )
    assert cycle.status_code == 422
    assert cycle.json()["error"]["code"] == "dependency_cycle"
    assert "backprop.step" in cycle.json()["error"]["message"]


def test_plan_waits_for_a_completed_diagnosis(client, provider) -> None:
    account = _signup(client, "Ada", "ada-wait-plan@example.com")
    topic = _topic(client, "Backpropagation", "wait-plan")
    _objective(client, topic["id"], "chain-rule.apply", "chain rule", "Apply the chain rule.")
    session = _session(client, account["learner_id"], topic["id"])
    missing = client.post(f"/api/sessions/{session['id']}/plan")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "diagnosis_not_found"
    provider.script = [_result(_questions(["chain-rule.apply"]))]
    started = client.post(f"/api/sessions/{session['id']}/diagnosis")
    assert started.status_code == 201
    early = client.post(f"/api/sessions/{session['id']}/plan")
    assert early.status_code == 409
    assert early.json()["error"]["code"] == "diagnosis_incomplete"


def test_missing_prerequisite_changes_the_starting_point(client, provider) -> None:
    account = _signup(client, "Ada", "ada-start@example.com")
    topic = _topic(client, "Backpropagation", "start-plan")
    _graph(client, topic["id"])
    codes = ["derivatives.basic", "backprop.step", "chain-rule.apply"]
    first = _session(client, account["learner_id"], topic["id"])
    _diagnose(
        client,
        provider,
        first["id"],
        codes,
        [
            _met("derivatives.basic"),
            _open("backprop.step"),
            _open("chain-rule.apply", understanding="partial", answer="partial", reasoning="partial"),
        ],
    )
    created = client.post(f"/api/sessions/{first['id']}/plan")
    assert created.status_code == 201, created.text
    plan = created.json()
    assert plan["session_status"] == "PLAN_READY"
    assert [step["objective_code"] for step in plan["steps"]] == [
        "derivatives.basic",
        "chain-rule.apply",
        "backprop.step",
    ]
    chain = next(step for step in plan["steps"] if step["objective_code"] == "chain-rule.apply")
    backprop = next(step for step in plan["steps"] if step["objective_code"] == "backprop.step")
    derivatives = next(step for step in plan["steps"] if step["objective_code"] == "derivatives.basic")
    assert derivatives["status"] == "satisfied"
    assert derivatives["evidence"] == "observed"
    assert chain["status"] == "current"
    assert chain["evidence"] == "none"
    assert "Apply the chain rule." in chain["completion_criteria"]
    assert backprop["status"] == "upcoming"
    assert plan["starting_objective_code"] == "chain-rule.apply"
    assert plan["current_step_id"] == chain["id"]
    assert [item["name"] for item in plan["concepts"]] == ["derivatives", "chain rule", "backpropagation"]
    for step in plan["steps"]:
        assert step["objective_id"]
        assert step["objective_code"]
        assert step["objective_statement"] in step["completion_criteria"]

    second = _session(client, account["learner_id"], topic["id"])
    _diagnose(
        client,
        provider,
        second["id"],
        codes,
        [_met("derivatives.basic"), _open("backprop.step"), _met("chain-rule.apply")],
    )
    ready = client.post(f"/api/sessions/{second['id']}/plan")
    assert ready.status_code == 201, ready.text
    assert ready.json()["starting_objective_code"] == "backprop.step"
    assert [step["objective_code"] for step in ready.json()["steps"] if step["status"] == "satisfied"] == [
        "derivatives.basic",
        "chain-rule.apply",
    ]


def test_plan_progress_persists_and_stays_private(client, provider) -> None:
    account = _signup(client, "Ada", "ada-persist-plan@example.com")
    topic = _topic(client, "Backpropagation", "persist-plan")
    _graph(client, topic["id"])
    session = _session(client, account["learner_id"], topic["id"])
    _diagnose(
        client,
        provider,
        session["id"],
        ["derivatives.basic", "backprop.step", "chain-rule.apply"],
        [_met("derivatives.basic"), _open("backprop.step"), _open("chain-rule.apply")],
    )
    created = client.post(f"/api/sessions/{session['id']}/plan")
    assert created.status_code == 201
    again = client.post(f"/api/sessions/{session['id']}/plan")
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "plan_exists"
    loaded = client.get(f"/api/sessions/{session['id']}/plan")
    assert loaded.status_code == 200
    assert loaded.json()["id"] == created.json()["id"]
    assert loaded.json()["revision"] == 1
    assert loaded.json()["current_step_id"] == created.json()["current_step_id"]
    assert [step["status"] for step in loaded.json()["steps"]] == [step["status"] for step in created.json()["steps"]]
    resumed = client.post(f"/api/sessions/{session['id']}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "PLAN_READY"
    after_resume = client.get(f"/api/sessions/{session['id']}/plan")
    assert after_resume.json()["revision"] == 1
    assert after_resume.json()["starting_objective_code"] == "chain-rule.apply"

    from app.db.session import get_sessionmaker
    from app.models.planning import LearningPlan

    fresh = get_sessionmaker()()
    try:
        stored = fresh.get(LearningPlan, UUID(created.json()["id"]))
        assert stored is not None
        assert stored.status == "active"
        assert stored.current_step_id == UUID(created.json()["current_step_id"])
    finally:
        fresh.close()

    client.cookies.clear()
    _signup(client, "Grace", "grace-persist-plan@example.com")
    hidden = client.get(f"/api/sessions/{session['id']}/plan")
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "session_not_found"


def test_new_diagnostic_evidence_revises_the_plan(client, provider) -> None:
    account = _signup(client, "Ada", "ada-revise-plan@example.com")
    topic = _topic(client, "Backpropagation", "revise-plan")
    _graph(client, topic["id"])
    codes = ["derivatives.basic", "backprop.step", "chain-rule.apply"]
    session = _session(client, account["learner_id"], topic["id"])
    _diagnose(
        client,
        provider,
        session["id"],
        codes,
        [_met("derivatives.basic"), _open("backprop.step"), _open("chain-rule.apply", understanding="partial", answer="partial", reasoning="partial")],
    )
    original = client.post(f"/api/sessions/{session['id']}/plan")
    assert original.status_code == 201
    assert original.json()["starting_objective_code"] == "chain-rule.apply"
    unchanged = client.post(f"/api/sessions/{session['id']}/plan/revision")
    assert unchanged.status_code == 409
    assert unchanged.json()["error"]["code"] == "plan_unchanged"
    provider.script = [_result("not json")]
    rejected = client.post(f"/api/sessions/{session['id']}/diagnosis/follow-up")
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "malformed_output"
    assert client.get(f"/api/sessions/{session['id']}/plan").json()["revision"] == 1
    _follow_up(
        client,
        provider,
        session["id"],
        codes,
        [_met("derivatives.basic"), _open("backprop.step"), _met("chain-rule.apply")],
    )
    revised = client.post(f"/api/sessions/{session['id']}/plan/revision")
    assert revised.status_code == 200, revised.text
    body = revised.json()
    assert body["revision"] == 2
    assert body["id"] != original.json()["id"]
    assert body["starting_objective_code"] == "backprop.step"
    chain = next(step for step in body["steps"] if step["objective_code"] == "chain-rule.apply")
    assert chain["status"] == "satisfied"
    assert chain["evidence"] == "observed"
    assert client.get(f"/api/sessions/{session['id']}").json()["status"] == "PLAN_READY"
    same = client.post(f"/api/sessions/{session['id']}/plan/revision")
    assert same.status_code == 409
    assert same.json()["error"]["code"] == "plan_unchanged"


def test_weak_reasoning_does_not_satisfy_a_step(client, provider) -> None:
    account = _signup(client, "Ada", "ada-weak-plan@example.com")
    topic = _topic(client, "Chain rule", "weak-plan")
    _objective(client, topic["id"], "chain-rule.apply", "chain rule", "Apply the chain rule.")
    session = _session(client, account["learner_id"], topic["id"])
    _diagnose(
        client,
        provider,
        session["id"],
        ["chain-rule.apply"],
        [_open("chain-rule.apply", understanding="partial", answer="correct", reasoning="weak")],
    )
    plan = client.post(f"/api/sessions/{session['id']}/plan")
    assert plan.status_code == 201, plan.text
    step = plan.json()["steps"][0]
    assert step["objective_code"] == "chain-rule.apply"
    assert step["status"] == "current"
    assert step["evidence"] == "none"
