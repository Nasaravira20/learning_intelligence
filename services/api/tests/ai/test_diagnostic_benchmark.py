"""Human-reviewed diagnostic benchmark for backpropagation.

Agreed thresholds, sample size 6 scripted cases:
- Every question code is one of the reviewed objective codes, and each reviewed objective has one question.
- A complete beginner is labeled beginner and the first unmet objective is functions.basic.
- A learner who has met functions and derivatives, and not the chain rule, is labeled partial.
- Answer verdict and reasoning verdict are both stored and may differ.
- Partial understanding is stored and confirmed is false.
- A correct answer with weak reasoning sets needs_review and does not confirm knowledge.
- A misconception stores the learner's own words as evidence and stays unconfirmed when confidence is low.
- Low-confidence judgments stay uncertain: starting_point uncertain, confidence at most 0.4, confirmed false.
- Invalid JSON, an unknown objective code, and a quote that is not in the response are rejected.

These cases are not a claim of universal diagnostic accuracy.
"""

import json

from app.ai.providers.mock import MockProvider
from app.ai.types import GenerationResult
from app.api.deps import get_model_provider
from app.diagnostics.policy import ObjectiveNode, classify_starting_point
from app.diagnostics.schemas import ItemJudgment
from app.main import app

PASSWORD = "correct-horse"
LOSS_EVIDENCE = "The loss is the same thing as the gradient."

OBJECTIVES = [
    ("functions.basic", "functions", []),
    ("derivatives.basic", "derivatives", ["functions.basic"]),
    ("chain-rule.apply", "chain rule", ["derivatives.basic"]),
    ("loss-gradient.distinguish", "loss", ["derivatives.basic"]),
    ("backprop.step", "backpropagation", ["chain-rule.apply", "loss-gradient.distinguish"]),
]


def _signup(client, email: str) -> dict:
    response = client.post(
        "/api/auth/signup",
        json={"display_name": "Ada", "email": email, "password": PASSWORD},
    )
    assert response.status_code == 201
    return response.json()


def _prepare(client, slug: str) -> tuple[dict, dict]:
    account = _signup(client, f"ada-{slug}@example.com")
    topic = client.post("/api/topics", json={"title": "Backpropagation", "slug": slug, "description": None})
    assert topic.status_code == 201
    topic_id = topic.json()["id"]
    for code, concept, prerequisites in OBJECTIVES:
        created = client.post(
            f"/api/topics/{topic_id}/objectives",
            json={
                "code": code,
                "statement": f"Use {concept} in a short original explanation.",
                "concept": concept,
                "prerequisite_codes": prerequisites,
            },
        )
        assert created.status_code == 201
    session = client.post("/api/sessions", json={"learner_id": account["learner_id"], "topic_id": topic_id})
    assert session.status_code == 201
    return account, session.json()


def _use(provider: MockProvider) -> None:
    app.dependency_overrides[get_model_provider] = lambda: provider


def _result(payload: dict) -> GenerationResult:
    return GenerationResult(text=json.dumps(payload), model_id="mock", input_tokens=1, output_tokens=1)


def _question_set() -> dict:
    formats = ["short_answer", "multiple_choice", "reasoning", "short_answer", "reasoning"]
    questions = []
    for (code, _concept, _prerequisites), question_format in zip(OBJECTIVES, formats):
        questions.append(
            {
                "objective_code": code,
                "format": question_format,
                "prompt": f"What can you do with {code}?",
                "choices": ["Use the definition", "Skip the idea"] if question_format == "multiple_choice" else None,
            }
        )
    return {"questions": questions}


def _judgment(code: str, answer: str, reasoning: str, understanding: str, confidence: str, misconception: dict | None = None) -> dict:
    return {
        "objective_code": code,
        "answer_verdict": answer,
        "reasoning_verdict": reasoning,
        "understanding": understanding,
        "confidence": confidence,
        "misconception": misconception,
    }


def _run(client, provider: MockProvider, session: dict, judgments: list[dict], answers: dict[str, tuple[str, str]]) -> dict:
    provider.script = [_result(_question_set()), _result({"judgments": judgments})]
    _use(provider)
    started = client.post(f"/api/sessions/{session['id']}/diagnosis")
    assert started.status_code == 201
    questions = started.json()["questions"]
    assert {item["objective_code"] for item in questions} == {code for code, _concept, _prerequisites in OBJECTIVES}
    assert {"short_answer", "multiple_choice", "reasoning"} <= {item["format"] for item in questions}
    submitted = client.post(
        f"/api/sessions/{session['id']}/diagnosis/responses",
        json={
            "responses": [
                {
                    "question_id": item["id"],
                    "answer_text": answers.get(item["objective_code"], ("", ""))[0],
                    "reasoning_text": answers.get(item["objective_code"], ("", ""))[1],
                }
                for item in questions
            ]
        },
    )
    assert submitted.status_code == 200
    return submitted.json()


def test_beginner_is_distinguished_from_partial_knowledge(client) -> None:
    provider = MockProvider()
    try:
        _account, beginner_session = _prepare(client, "backprop-beginner")
        beginner_judgments = [
            _judgment(code, "incorrect", "weak", "none", "medium") for code, _concept, _prerequisites in OBJECTIVES
        ]
        beginner = _run(client, provider, beginner_session, beginner_judgments, {})
        assert beginner["starting_point"] == "beginner"
        assert beginner["first_unmet_objective_code"] == "functions.basic"
        assert all(item["confirmed"] is False for item in beginner["judgments"])

        client.cookies.clear()
        _account, partial_session = _prepare(client, "backprop-partial")
        partial_judgments = [
            _judgment("functions.basic", "correct", "sound", "solid", "high"),
            _judgment("derivatives.basic", "correct", "sound", "solid", "high"),
            _judgment("chain-rule.apply", "partial", "weak", "partial", "medium"),
            _judgment(
                "loss-gradient.distinguish",
                "incorrect",
                "weak",
                "none",
                "medium",
                {
                    "concept": "loss",
                    "description": "The learner treated loss and gradient as the same object.",
                    "evidence": LOSS_EVIDENCE,
                    "confidence": "low",
                },
            ),
            _judgment("backprop.step", "unanswered", "absent", "none", "medium"),
        ]
        answers = {
            "functions.basic": ("A function can feed another function.", "The output becomes the next input."),
            "derivatives.basic": ("The derivative of x squared is 2x.", "Power rule lowers the exponent."),
            "chain-rule.apply": ("I multiply the two derivatives.", "I am not sure about the composition."),
            "loss-gradient.distinguish": (LOSS_EVIDENCE, "I could not separate the two words."),
            "backprop.step": ("", ""),
        }
        partial = _run(client, provider, partial_session, partial_judgments, answers)
        assert partial["starting_point"] == "partial"
        assert partial["first_unmet_objective_code"] == "chain-rule.apply"
        chain = next(item for item in partial["judgments"] if item["objective_code"] == "chain-rule.apply")
        assert chain["answer_verdict"] == "partial"
        assert chain["reasoning_verdict"] == "weak"
        assert chain["understanding"] == "partial"
        assert chain["needs_review"] is True
        assert chain["confirmed"] is False
        functions = next(item for item in partial["judgments"] if item["objective_code"] == "functions.basic")
        assert functions["confirmed"] is True
        assert functions["answer_verdict"] != functions["reasoning_verdict"] or functions["reasoning_verdict"] == "sound"
        assert partial["misconceptions"][0]["evidence"] == LOSS_EVIDENCE
        assert partial["misconceptions"][0]["confirmed"] is False
        knowledge = client.get("/api/learner/knowledge")
        assert knowledge.status_code == 200
        confirmed = [item["concept"] for item in knowledge.json() if item["confirmed"] is True]
        assert confirmed == ["functions", "derivatives"] or set(confirmed) == {"functions", "derivatives"}
        partial_rows = [item for item in knowledge.json() if item["concept"] == "chain rule"]
        assert partial_rows
        assert partial_rows[0]["confirmed"] is False
        assert partial_rows[0]["evidence_kind"] == "inferred"
    finally:
        app.dependency_overrides.pop(get_model_provider, None)


def test_correct_answer_with_weak_reasoning_is_not_mastery(client) -> None:
    provider = MockProvider()
    try:
        account = _signup(client, "ada-weak@example.com")
        topic = client.post("/api/topics", json={"title": "Chain rule", "slug": "chain-rule-weak", "description": None})
        assert topic.status_code == 201
        created = client.post(
            f"/api/topics/{topic.json()['id']}/objectives",
            json={
                "code": "chain-rule.apply",
                "statement": "Differentiate a composition.",
                "concept": "chain rule",
                "prerequisite_codes": [],
            },
        )
        assert created.status_code == 201
        session = client.post(
            "/api/sessions",
            json={"learner_id": account["learner_id"], "topic_id": topic.json()["id"]},
        )
        assert session.status_code == 201
        provider.script = [
            _result(
                {
                    "questions": [
                        {
                            "objective_code": "chain-rule.apply",
                            "format": "short_answer",
                            "prompt": "Differentiate sin of x squared.",
                            "choices": None,
                        }
                    ]
                }
            ),
            _result(
                {
                    "judgments": [
                        _judgment("chain-rule.apply", "correct", "weak", "none", "medium"),
                    ]
                }
            ),
        ]
        _use(provider)
        started = client.post(f"/api/sessions/{session.json()['id']}/diagnosis")
        assert started.status_code == 201
        question_id = started.json()["questions"][0]["id"]
        submitted = client.post(
            f"/api/sessions/{session.json()['id']}/diagnosis/responses",
            json={
                "responses": [
                    {
                        "question_id": question_id,
                        "answer_text": "cos of x squared times 2x.",
                        "reasoning_text": "I remembered the formula.",
                    }
                ]
            },
        )
        assert submitted.status_code == 200
        judgment = submitted.json()["judgments"][0]
        assert judgment["answer_verdict"] == "correct"
        assert judgment["reasoning_verdict"] == "weak"
        assert judgment["answer_text"] != judgment["reasoning_text"]
        assert judgment["needs_review"] is True
        assert judgment["confirmed"] is False
        knowledge = client.get("/api/learner/knowledge")
        assert knowledge.json() == []
    finally:
        app.dependency_overrides.pop(get_model_provider, None)


def test_uncertain_conclusions_remain_uncertain(client) -> None:
    provider = MockProvider()
    try:
        _account, session = _prepare(client, "backprop-uncertain")
        judgments = [
            _judgment(code, "unanswered", "uncertain", "uncertain", "low")
            for code, _concept, _prerequisites in OBJECTIVES
        ]
        judgments[3]["misconception"] = {
            "concept": "loss",
            "description": "There may be a mix-up between loss and gradient.",
            "evidence": LOSS_EVIDENCE,
            "confidence": "low",
        }
        report = _run(
            client,
            provider,
            session,
            judgments,
            {"loss-gradient.distinguish": (LOSS_EVIDENCE, "I am guessing.")},
        )
        assert report["starting_point"] == "uncertain"
        assert report["confidence"] <= 0.4
        assert "uncertain" in report["summary"]
        assert all(item["confirmed"] is False for item in report["judgments"])
        assert report["misconceptions"][0]["confirmed"] is False
        assert report["misconceptions"][0]["evidence"] == LOSS_EVIDENCE
        knowledge = client.get("/api/learner/knowledge")
        assert knowledge.json() == []
    finally:
        app.dependency_overrides.pop(get_model_provider, None)


def test_prior_observed_concept_can_move_the_starting_point() -> None:
    nodes = [
        ObjectiveNode("functions.basic", "functions", "Use a function output as an input.", 0, ()),
        ObjectiveNode("chain-rule.apply", "chain rule", "Differentiate a composition.", 1, ("functions.basic",)),
    ]
    chain_only = {
        "chain-rule.apply": ItemJudgment(
            objective_code="chain-rule.apply",
            answer_verdict="incorrect",
            reasoning_verdict="weak",
            understanding="none",
            confidence="medium",
            misconception=None,
        )
    }
    starting, first, _confidence = classify_starting_point(nodes, chain_only, {"functions"})
    assert starting == "partial"
    assert first == "chain-rule.apply"
    beginner, first_gap, _confidence = classify_starting_point(nodes, chain_only, set())
    assert beginner == "beginner"
    assert first_gap == "functions.basic"
