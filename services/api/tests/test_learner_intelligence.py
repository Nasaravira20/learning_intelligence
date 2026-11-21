import logging
from uuid import uuid4

from sqlalchemy import create_engine, func, select, text

PASSWORD = "correct-horse"
SECRET_SUMMARY = "PromptShouldNotBeLoggedXYZ"
SECRET_NAME = "NameShouldNotBeLoggedXYZ"


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


def _knowledge(client, topic_id: str, **overrides) -> dict:
    payload = {
        "topic_id": topic_id,
        "concept": "chain rule",
        "summary": "Can differentiate a composition.",
        "evidence_kind": "inferred",
        "confidence": 0.25,
        "provenance": "learner_report",
    }
    payload.update(overrides)
    return payload


def test_evidence_pairs_reject_inferred_as_observed() -> None:
    from app.learner.evidence import is_confirmed, pair_is_valid

    assert pair_is_valid("observed", "assessment") is True
    assert pair_is_valid("observed", "learner_response") is True
    assert pair_is_valid("inferred", "system_estimate") is True
    assert pair_is_valid("inferred", "learner_report") is True
    assert pair_is_valid("observed", "learner_report") is False
    assert pair_is_valid("inferred", "assessment") is False
    assert is_confirmed("observed") is True
    assert is_confirmed("inferred") is False


def test_private_dashboard_requires_sign_in(client) -> None:
    response = client.get("/api/learner")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"
    history = client.get(f"/api/sessions/{uuid4()}/history")
    assert history.status_code == 401


def test_profile_goal_preference_and_confidence_persist(client) -> None:
    account = _signup(client, "Ada", "ada-profile@example.com")
    topic = _topic(client, "Chain rule", "chain-rule")
    before = client.get("/api/learner")
    assert before.status_code == 200
    assert before.json()["profile"]["display_name"] == "Ada"
    assert before.json()["profile"]["background_note"] is None

    corrected = client.patch(
        "/api/learner/profile",
        json={"display_name": "Augusta Ada", "background_note": "I know basic derivatives."},
    )
    assert corrected.status_code == 200
    assert corrected.json()["display_name"] == "Augusta Ada"
    assert corrected.json()["background_note"] == "I know basic derivatives."

    preferences = client.put(
        "/api/learner/preferences",
        json={"pace": "unhurried", "explanation_detail": "thorough", "practice_first": True, "notes": "Examples first."},
    )
    assert preferences.status_code == 200

    goal = client.post(
        "/api/learner/goals",
        json={"statement": "Use the chain rule without mixing it up with the product rule.", "topic_id": topic["id"]},
    )
    assert goal.status_code == 201
    finished = client.patch(f"/api/learner/goals/{goal.json()['id']}", json={"status": "completed"})
    assert finished.status_code == 200
    assert finished.json()["status"] == "completed"

    knowledge = client.post("/api/learner/knowledge", json=_knowledge(client, topic["id"]))
    assert knowledge.status_code == 201
    assert knowledge.json()["confidence"] == 0.25
    assert knowledge.json()["topic_id"] == topic["id"]
    assert knowledge.json()["evidence_kind"] == "inferred"
    assert knowledge.json()["confirmed"] is False

    dashboard = client.get("/api/learner")
    body = dashboard.json()
    assert body["profile"]["display_name"] == "Augusta Ada"
    assert body["preferences"]["pace"] == "unhurried"
    assert body["preferences"]["practice_first"] is True
    assert body["goals"][0]["status"] == "completed"
    assert body["knowledge"][0]["confidence"] == 0.25
    assert client.get("/api/auth/me").json()["display_name"] == "Augusta Ada"

    public = client.get(f"/api/learners/{account['learner_id']}")
    assert public.status_code == 200
    assert "background_note" not in public.json()
    assert "knowledge" not in public.json()


def test_knowledge_is_topic_specific_and_history_keeps_both_kinds(client) -> None:
    _signup(client, "Ada", "ada-knowledge@example.com")
    chain = _topic(client, "Chain rule", "chain-rule-topic")
    product = _topic(client, "Product rule", "product-rule")

    inferred = client.post("/api/learner/knowledge", json=_knowledge(client, chain["id"], summary=SECRET_SUMMARY))
    assert inferred.status_code == 201
    observed = client.post(
        "/api/learner/knowledge",
        json=_knowledge(
            client,
            product["id"],
            concept="product rule",
            summary="Demonstrated the product rule on a polynomial.",
            evidence_kind="observed",
            provenance="assessment",
            confidence=0.75,
        ),
    )
    assert observed.status_code == 201
    assert observed.json()["confirmed"] is True
    assert observed.json()["evidence_kind"] == "observed"

    mismatch = client.post(
        "/api/learner/knowledge",
        json=_knowledge(client, chain["id"], evidence_kind="observed", provenance="learner_report"),
    )
    assert mismatch.status_code == 422
    too_sure = client.post("/api/learner/knowledge", json=_knowledge(client, chain["id"], confidence=1.4))
    assert too_sure.status_code == 422

    chain_only = client.get("/api/learner/knowledge", params={"topic_id": chain["id"]})
    assert chain_only.status_code == 200
    assert [item["topic_id"] for item in chain_only.json()] == [chain["id"]]

    corrected = client.patch(
        f"/api/learner/knowledge/{inferred.json()['id']}",
        json={"summary": "I have not demonstrated the chain rule.", "correction_note": "That self-report was too strong."},
    )
    assert corrected.status_code == 200
    assert corrected.json()["evidence_kind"] == "inferred"
    assert corrected.json()["confirmed"] is False
    assert corrected.json()["provenance"] == "learner_report"
    assert corrected.json()["replaces_id"] == inferred.json()["id"]

    current = client.get("/api/learner/knowledge", params={"topic_id": chain["id"]})
    assert [item["summary"] for item in current.json()] == ["I have not demonstrated the chain rule."]
    trail = client.get("/api/learner/knowledge", params={"topic_id": chain["id"], "history": "true"})
    assert [item["summary"] for item in trail.json()] == [
        SECRET_SUMMARY,
        "I have not demonstrated the chain rule.",
    ]

    promoted = client.patch(
        f"/api/learner/knowledge/{corrected.json()['id']}",
        json={"evidence_kind": "observed", "provenance": "assessment", "summary": "Now observed.", "correction_note": "No."},
    )
    assert promoted.status_code == 422


def test_assessment_activity_and_misconception_history(client) -> None:
    account = _signup(client, "Ada", "ada-history@example.com")
    topic = _topic(client, "Chain rule", "chain-rule-history")
    other = _topic(client, "Limits", "limits")
    created = client.post(
        "/api/sessions",
        json={"learner_id": account["learner_id"], "topic_id": topic["id"]},
    )
    assert created.status_code == 201
    session_id = created.json()["id"]

    first = client.post(
        "/api/learner/assessments",
        json={
            "topic_id": topic["id"],
            "session_id": session_id,
            "prompt_summary": "Differentiate sin(x^2).",
            "response_summary": "I multiplied by the inside and stopped.",
            "outcome": "partial",
        },
    )
    assert first.status_code == 201
    second = client.post(
        "/api/learner/assessments",
        json={
            "topic_id": topic["id"],
            "prompt_summary": "State the chain rule in words.",
            "response_summary": "Derivative of the outside, then multiply by the inside derivative.",
            "outcome": "recorded",
        },
    )
    assert second.status_code == 201
    listed = client.get("/api/learner/assessments")
    assert [item["prompt_summary"] for item in listed.json()] == [
        "Differentiate sin(x^2).",
        "State the chain rule in words.",
    ]

    other_topic = client.post(
        "/api/learner/assessments",
        json={
            "topic_id": other["id"],
            "session_id": session_id,
            "prompt_summary": "Wrong session topic.",
            "response_summary": "Should not attach.",
            "outcome": "recorded",
        },
    )
    assert other_topic.status_code == 422
    assert other_topic.json()["error"]["code"] == "session_topic_mismatch"

    activity = client.post(
        "/api/learner/activities",
        json={
            "topic_id": topic["id"],
            "session_id": session_id,
            "activity_kind": "practice",
            "summary": "Worked two chain-rule items.",
        },
    )
    assert activity.status_code == 201
    client.post(
        "/api/learner/activities",
        json={"topic_id": other["id"], "activity_kind": "note", "summary": "Limits note that this session should hide."},
    )

    misconception = client.post(
        "/api/learner/misconceptions",
        json={
            "topic_id": topic["id"],
            "concept": "chain rule",
            "description": "The chain rule is the same as multiplying the two derivatives without composition.",
            "evidence_kind": "inferred",
            "confidence": 0.4,
            "provenance": "learner_report",
            "supporting_note": "The partial answer stopped after the outer derivative.",
        },
    )
    assert misconception.status_code == 201
    assert misconception.json()["confirmed"] is False
    rejected = client.patch(
        f"/api/learner/misconceptions/{misconception.json()['id']}",
        json={"status": "rejected", "correction_note": "I do not hold this mix-up."},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["evidence_kind"] == "inferred"
    assert rejected.json()["confirmed"] is False

    history = client.get(f"/api/sessions/{session_id}/history")
    assert history.status_code == 200
    body = history.json()
    assert body["topic_id"] == topic["id"]
    assert body["topic_title"] == "Chain rule"
    assert len(body["assessments"]) == 2
    assert [item["summary"] for item in body["activities"]] == ["Worked two chain-rule items."]
    assert body["misconceptions"][-1]["status"] == "rejected"
    assert all(item["topic_id"] == topic["id"] for item in body["assessments"])


def test_one_learner_cannot_read_another_learners_records(client) -> None:
    ada = _signup(client, "Ada", "ada-private@example.com")
    topic = _topic(client, "Chain rule", "chain-rule-private")
    knowledge = client.post("/api/learner/knowledge", json=_knowledge(client, topic["id"], summary="Ada's private note."))
    assert knowledge.status_code == 201
    session = client.post(
        "/api/sessions",
        json={"learner_id": ada["learner_id"], "topic_id": topic["id"]},
    )
    assert session.status_code == 201
    client.patch("/api/learner/profile", json={"background_note": "Only Ada should see this note."})

    client.cookies.clear()
    _signup(client, "Grace", "grace-private@example.com")
    stolen = client.patch(
        f"/api/learner/knowledge/{knowledge.json()['id']}",
        json={"summary": "Taken.", "correction_note": "Not Grace's record."},
    )
    assert stolen.status_code == 404
    assert stolen.json()["error"]["code"] == "knowledge_not_found"
    history = client.get(f"/api/sessions/{session.json()['id']}/history")
    assert history.status_code == 404
    assert history.json()["error"]["code"] == "session_not_found"
    dashboard = client.get("/api/learner")
    assert dashboard.status_code == 200
    assert dashboard.json()["knowledge"] == []
    assert dashboard.json()["profile"]["display_name"] == "Grace"
    assert "Ada's private note." not in dashboard.text
    assert "Only Ada should see this note." not in dashboard.text


def test_restart_and_logs_keep_records_without_secrets_or_model_calls(client) -> None:
    _signup(client, SECRET_NAME, "secret-name@example.com")
    topic = _topic(client, "Chain rule", "chain-rule-restart")
    handler = _capture_logs()
    try:
        updated = client.patch("/api/learner/profile", json={"display_name": "Kept After Restart"})
        assert updated.status_code == 200
        recorded = client.post("/api/learner/knowledge", json=_knowledge(client, topic["id"], summary=SECRET_SUMMARY))
        assert recorded.status_code == 201
    finally:
        logging.getLogger().removeHandler(handler)

    rendered = "\n".join(handler.lines)
    assert SECRET_NAME not in rendered
    assert SECRET_SUMMARY not in rendered
    assert "secret-name@example.com" not in rendered

    from app.core.config import get_settings
    from app.db.session import get_engine, get_sessionmaker
    from app.models import AiUsageRecord

    fresh = create_engine(get_settings().database_url)
    with fresh.connect() as connection:
        names = connection.execute(text("SELECT display_name FROM learner_profiles")).scalars().all()
    fresh.dispose()
    assert "Kept After Restart" in names

    get_engine().dispose()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
    again = client.get("/api/learner")
    assert again.status_code == 200
    assert again.json()["profile"]["display_name"] == "Kept After Restart"
    assert again.json()["knowledge"][0]["summary"] == SECRET_SUMMARY
    assert again.json()["knowledge"][0]["confirmed"] is False

    with get_sessionmaker()() as db:
        usage = db.scalar(select(func.count()).select_from(AiUsageRecord))
    assert usage == 0
