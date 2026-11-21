import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import NullPool


SECRET_NAME = "NameShouldNotBeLoggedXYZ"
SECRET_URL = "postgresql+psycopg://ai_teacher:supersecret@db/ai_teacher"


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


def test_migrations_create_expected_tables(client) -> None:
    from app.db.session import get_engine

    with get_engine().connect() as connection:
        names = set(
            connection.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            ).scalars()
        )
    assert {
        "users",
        "learner_profiles",
        "learning_topics",
        "learning_sessions",
        "ai_usage_records",
        "ai_model_checks",
        "learning_goals",
        "learning_preferences",
        "learner_knowledge",
        "misconception_records",
        "assessment_records",
        "learning_activities",
        "learning_objectives",
        "objective_prerequisites",
        "diagnostic_attempts",
        "diagnostic_questions",
        "diagnostic_responses",
        "topic_concepts",
        "learning_plans",
        "learning_plan_steps",
    } <= names


def test_health_ok(client) -> None:
    response = client.get("/health", headers={"X-Request-ID": "req-health"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    assert response.headers["x-request-id"] == "req-health"


def test_health_reports_database_outage(client, monkeypatch) -> None:
    def fail() -> None:
        raise OperationalError("SELECT 1", {}, Exception(SECRET_URL))

    handler = _capture_logs()
    monkeypatch.setattr("app.api.health.ping_database", fail)
    response = client.get("/health", headers={"X-Request-ID": "req-down"})
    logging.getLogger().removeHandler(handler)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_unavailable"
    assert response.json()["error"]["request_id"] == "req-down"
    assert "supersecret" not in response.text
    assert "supersecret" not in "\n".join(handler.lines)
    assert any("health_check_failed" in line for line in handler.lines)


def test_unknown_route_returns_json(client) -> None:
    response = client.get("/missing", headers={"X-Request-ID": "req-missing"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.headers["x-request-id"] == "req-missing"


def test_invalid_json_and_blank_name_are_validation_errors(client) -> None:
    invalid = client.post(
        "/api/learners",
        content="{",
        headers={"content-type": "application/json", "X-Request-ID": "req-json"},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
    assert invalid.json()["error"]["request_id"] == "req-json"

    blank = client.post("/api/learners", json={"display_name": "   "})
    assert blank.status_code == 422
    assert blank.json()["error"]["details"][0]["field"] == "display_name"

    extra = client.post("/api/learners", json={"display_name": "Ada", "role": "admin"})
    assert extra.status_code == 422


def test_learner_topic_and_session_round_trip(client, migrated_database: str) -> None:
    handler = _capture_logs()
    created = client.post("/api/learners", json={"display_name": SECRET_NAME})
    assert created.status_code == 201
    learner = created.json()
    assert learner["display_name"] == SECRET_NAME
    assert SECRET_NAME not in "\n".join(handler.lines)

    fetched = client.get(f"/api/learners/{learner['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == learner["id"]

    missing = client.get(f"/api/learners/{uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "learner_not_found"

    invalid_id = client.get("/api/learners/not-a-uuid")
    assert invalid_id.status_code == 422
    assert invalid_id.json()["error"]["code"] == "validation_error"

    topic = client.post(
        "/api/topics",
        json={"title": "Chain rule", "slug": "chain-rule", "description": "Prerequisite"},
    )
    assert topic.status_code == 201
    topic_body = topic.json()

    duplicate = client.post(
        "/api/topics",
        json={"title": "Chain rule again", "slug": "chain-rule"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "topic_slug_taken"

    bad_slug = client.post("/api/topics", json={"title": "Bad", "slug": "Bad Slug"})
    assert bad_slug.status_code == 422

    session_response = client.post(
        "/api/sessions",
        json={"learner_id": learner["id"], "topic_id": topic_body["id"]},
    )
    assert session_response.status_code == 201
    learning_session = session_response.json()
    assert learning_session["status"] == "TOPIC_SELECTED"
    assert learning_session["resumed_at"] is None
    assert learning_session["learner_name"] == SECRET_NAME
    assert learning_session["topic_slug"] == "chain-rule"

    missing_learner = client.post(
        "/api/sessions",
        json={"learner_id": str(uuid4()), "topic_id": topic_body["id"]},
    )
    assert missing_learner.status_code == 404
    assert missing_learner.json()["error"]["code"] == "learner_not_found"

    other = create_engine(migrated_database, poolclass=NullPool)
    with other.begin() as connection:
        connection.execute(
            text("UPDATE learning_sessions SET resumed_at = :resumed_at WHERE id = :id"),
            {
                "id": learning_session["id"],
                "resumed_at": datetime(2000, 1, 1, tzinfo=timezone.utc),
            },
        )
    resumed = client.post(f"/api/sessions/{learning_session['id']}/resume")
    assert resumed.status_code == 200
    resumed_body = resumed.json()
    assert resumed_body["status"] == "TOPIC_SELECTED"
    assert not str(resumed_body["resumed_at"]).startswith("2000")

    with other.connect() as connection:
        row = connection.execute(
            text("SELECT status, resumed_at FROM learning_sessions WHERE id = :id"),
            {"id": learning_session["id"]},
        ).one()
    other.dispose()
    assert row.status == "TOPIC_SELECTED"
    assert row.resumed_at is not None

    listed = client.get("/api/sessions")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == learning_session["id"]

    unknown = client.post(f"/api/sessions/{uuid4()}/resume")
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "session_not_found"
    logging.getLogger().removeHandler(handler)


def test_unhandled_exception_is_hidden(client) -> None:
    from app.main import app

    if not any(getattr(route, "path", None) == "/__test/boom" for route in app.routes):

        @app.get("/__test/boom")
        def boom() -> None:
            raise RuntimeError(SECRET_URL)

    handler = _capture_logs()
    response = client.get("/__test/boom", headers={"X-Request-ID": "req-boom"})
    logging.getLogger().removeHandler(handler)
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "The request could not be completed."
    assert body["error"]["request_id"] == "req-boom"
    assert response.headers["x-request-id"] == "req-boom"
    assert "supersecret" not in response.text
    rendered = "\n".join(handler.lines)
    assert "supersecret" not in rendered
    assert "unhandled_exception" in rendered or "unhandled_error" in rendered
