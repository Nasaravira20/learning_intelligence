import json

from app.ai.providers.mock import MockProvider
from app.ai.types import GenerationResult
from app.api.deps import get_model_provider
from app.main import app

PASSWORD = "correct-horse"
HIDDEN = "Apply the inner change, then the outer change, for chain-rule.apply"


def _result(payload: object) -> GenerationResult:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return GenerationResult(text=text, model_id="mock", input_tokens=1, output_tokens=1)


def _planned_session(client, email: str) -> dict:
    account = client.post(
        "/api/auth/signup",
        json={"display_name": "Ada", "email": email, "password": PASSWORD},
    )
    assert account.status_code == 201
    topic = client.post(
        "/api/topics",
        json={"title": "Backpropagation", "slug": email.split("@")[0], "description": None},
    )
    assert topic.status_code == 201
    objective = client.post(
        f"/api/topics/{topic.json()['id']}/objectives",
        json={
            "code": "chain-rule.apply",
            "statement": "Apply the chain rule to a composed function.",
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
    selection = client.post(f"/api/sessions/{session.json()['id']}/pedagogy-selection", json={})
    assert selection.status_code == 201, selection.text
    return session.json()


def test_lesson_executes_selected_strategies_without_revealing_the_answer(client) -> None:
    session = _planned_session(client, "ada-teach@example.com")
    started = client.post(f"/api/sessions/{session['id']}/teaching")
    assert started.status_code == 201, started.text
    body = started.json()
    assert body["objective_code"] == "chain-rule.apply"
    assert body["session_status"] == "TEACHING"
    assert body["review_status"] == "pending_human_review"
    assert body["status"] == "active"
    strategy_ids = {item["strategy_id"] for item in body["activities"]}
    assert {"small_step_instruction", "concrete_examples", "worked_examples"} <= strategy_ids
    kinds = [item["kind"] for item in body["activities"]]
    assert "explanation" in kinds
    assert "concrete_example" in kinds
    assert "worked_example" in kinds
    check_at = kinds.index("check_for_understanding")
    assert check_at < len(kinds) - 1
    explanation = next(item for item in body["activities"] if item["kind"] == "explanation")
    assert explanation["example"]
    assert "chain-rule.apply" in explanation["prompt"]
    assert "expected_answer" not in started.text
    assert HIDDEN not in started.text
    hinted = client.post(f"/api/sessions/{session['id']}/teaching/hint")
    assert hinted.status_code == 200, hinted.text
    revealed = hinted.json()["activities"][0]["hints_revealed"]
    assert len(revealed) == 1
    assert HIDDEN not in revealed[0]["text"]
    resumed = client.post(f"/api/sessions/{session['id']}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "TEACHING"
    loaded = client.get(f"/api/sessions/{session['id']}/teaching")
    assert loaded.status_code == 200
    assert loaded.json()["id"] == body["id"]
    assert loaded.json()["activities"][0]["hints_revealed"][0]["text"] == revealed[0]["text"]
    again = client.post(f"/api/sessions/{session['id']}/teaching")
    assert again.status_code == 201
    assert again.json()["id"] == body["id"]


def test_correct_work_fades_support_and_a_struggle_inserts_help(client) -> None:
    session = _planned_session(client, "ada-fade@example.com")
    started = client.post(f"/api/sessions/{session['id']}/teaching")
    assert started.status_code == 201, started.text
    before = started.json()["activities"][1]
    assert before["support_level"] == "high"
    faded = client.post(
        f"/api/sessions/{session['id']}/teaching/attempt",
        json={"outcome": "correct", "answer_text": "I used the first part only."},
    )
    assert faded.status_code == 200, faded.text
    current = next(item for item in faded.json()["activities"] if item["status"] == "current")
    assert current["id"] == before["id"]
    assert current["support_level"] == "medium"
    assert faded.json()["session_status"] == "TEACHING"

    other = _planned_session(client, "ada-struggle@example.com")
    opened = client.post(f"/api/sessions/{other['id']}/teaching")
    assert opened.status_code == 201, opened.text
    original_ids = {item["id"] for item in opened.json()["activities"]}
    struggled = client.post(
        f"/api/sessions/{other['id']}/teaching/attempt",
        json={"outcome": "struggled", "answer_text": "I mixed the two parts together."},
    )
    assert struggled.status_code == 200, struggled.text
    lesson = struggled.json()
    assert len(lesson["activities"]) == len(original_ids) + 1
    current = next(item for item in lesson["activities"] if item["status"] == "current")
    assert current["id"] not in original_ids
    assert current["inserted_for_struggle"] is True
    assert current["support_level"] == "high"
    assert current["kind"] in {"explanation", "concrete_example", "worked_example"}
    assert current["strategy_id"] in {"small_step_instruction", "concrete_examples", "worked_examples"}
    assert lesson["session_status"] == "TEACHING"
    assert "MASTERED" not in struggled.text
    assert "EVALUATING" not in struggled.text


def test_rejected_lesson_does_not_start_teaching(client) -> None:
    provider = MockProvider()
    app.dependency_overrides[get_model_provider] = lambda: provider
    try:
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
        session = _planned_session(client, "ada-reject@example.com")
        provider.script.append(
            _result(
                {
                    "objective_code": "chain-rule.apply",
                    "activities": [
                        {
                            "strategy_id": "retrieval_practice",
                            "kind": "explanation",
                            "title": "Unselected strategy lesson",
                            "prompt": "Objective chain-rule.apply: this uses a strategy that was not selected.",
                            "example": "One case of the chain rule uses a short input and a short output.",
                            "worked_steps": [],
                            "expected_answer": None,
                            "hints": [],
                            "support_level": "high",
                        },
                        {
                            "strategy_id": "retrieval_practice",
                            "kind": "check_for_understanding",
                            "title": "Unselected strategy check",
                            "prompt": "Objective chain-rule.apply: answer the check.",
                            "example": None,
                            "worked_steps": [],
                            "expected_answer": HIDDEN,
                            "hints": [
                                {
                                    "text": "Name the first part of this objective before combining later parts.",
                                    "reveals_answer": False,
                                }
                            ],
                            "support_level": "high",
                        },
                    ],
                }
            )
        )
        rejected = client.post(f"/api/sessions/{session['id']}/teaching")
        assert rejected.status_code == 422
        assert rejected.json()["error"]["code"] == "malformed_output"
        saved = client.get(f"/api/sessions/{session['id']}")
        assert saved.json()["status"] == "PLAN_READY"
        missing = client.get(f"/api/sessions/{session['id']}/teaching")
        assert missing.status_code == 404
    finally:
        app.dependency_overrides.pop(get_model_provider, None)


def test_other_learner_cannot_read_a_lesson(client) -> None:
    session = _planned_session(client, "ada-private-teach@example.com")
    started = client.post(f"/api/sessions/{session['id']}/teaching")
    assert started.status_code == 201, started.text
    client.post("/api/auth/signout")
    other = client.post(
        "/api/auth/signup",
        json={"display_name": "Grace", "email": "grace-teach@example.com", "password": PASSWORD},
    )
    assert other.status_code == 201
    hidden = client.get(f"/api/sessions/{session['id']}/teaching")
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "session_not_found"


def test_teaching_waits_for_a_strategy_choice(client) -> None:
    account = client.post(
        "/api/auth/signup",
        json={"display_name": "Ada", "email": "ada-early-teach@example.com", "password": PASSWORD},
    )
    topic = client.post(
        "/api/topics",
        json={"title": "Backpropagation", "slug": "ada-early-teach", "description": None},
    )
    client.post(
        f"/api/topics/{topic.json()['id']}/objectives",
        json={
            "code": "chain-rule.apply",
            "statement": "Apply the chain rule.",
            "concept": "chain rule",
            "prerequisite_codes": [],
        },
    )
    session = client.post(
        "/api/sessions",
        json={"learner_id": account.json()["learner_id"], "topic_id": topic.json()["id"]},
    )
    started = client.post(f"/api/sessions/{session.json()['id']}/teaching")
    assert started.status_code == 409
    assert started.json()["error"]["code"] == "teaching_not_ready"
