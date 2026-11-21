import logging

PASSWORD = "correct-horse"


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


def test_signup_signin_and_signout(client) -> None:
    handler = _capture_logs()
    created = client.post(
        "/api/auth/signup",
        json={"display_name": "Ada Lovelace", "email": "Ada@Example.com", "password": PASSWORD},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["email"] == "ada@example.com"
    assert body["display_name"] == "Ada Lovelace"
    assert "password" not in body
    assert client.cookies.get("ai_teacher_session")

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["learner_id"] == body["learner_id"]

    duplicate = client.post(
        "/api/auth/signup",
        json={"display_name": "Ada", "email": "ada@example.com", "password": PASSWORD},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "email_taken"

    client.cookies.clear()
    wrong = client.post(
        "/api/auth/signin",
        json={"email": "ada@example.com", "password": "not-the-password"},
    )
    assert wrong.status_code == 401
    assert wrong.json()["error"]["code"] == "invalid_credentials"
    assert client.cookies.get("ai_teacher_session") is None

    missing = client.post(
        "/api/auth/signin",
        json={"email": "missing@example.com", "password": PASSWORD},
    )
    assert missing.status_code == 401
    assert missing.json()["error"]["message"] == wrong.json()["error"]["message"]

    signed_in = client.post(
        "/api/auth/signin",
        json={"email": "ada@example.com", "password": PASSWORD},
    )
    assert signed_in.status_code == 200
    assert client.cookies.get("ai_teacher_session")

    signed_out = client.post("/api/auth/signout")
    assert signed_out.status_code == 200
    assert client.get("/api/auth/me").status_code == 401

    rendered = "\n".join(handler.lines)
    assert PASSWORD not in rendered
    assert "ada@example.com" not in rendered
    logging.getLogger().removeHandler(handler)


def test_signed_in_learner_only_sees_their_sessions(client) -> None:
    ada = client.post(
        "/api/auth/signup",
        json={"display_name": "Ada", "email": "ada@example.com", "password": PASSWORD},
    )
    assert ada.status_code == 201
    topic = client.post(
        "/api/topics",
        json={"title": "Chain rule", "slug": "chain-rule", "description": None},
    )
    assert topic.status_code == 201
    created = client.post(
        "/api/sessions",
        json={"learner_id": ada.json()["learner_id"], "topic_id": topic.json()["id"]},
    )
    assert created.status_code == 201
    session_id = created.json()["id"]

    client.cookies.clear()
    bob = client.post(
        "/api/auth/signup",
        json={"display_name": "Grace", "email": "grace@example.com", "password": PASSWORD},
    )
    assert bob.status_code == 201
    hidden = client.get(f"/api/sessions/{session_id}")
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "session_not_found"
    assert client.get("/api/sessions").json() == []

    client.cookies.clear()
    listed = client.get("/api/sessions")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == session_id


def test_short_password_is_rejected(client) -> None:
    response = client.post(
        "/api/auth/signup",
        json={"display_name": "Ada", "email": "short@example.com", "password": "tiny"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "tiny" not in response.text
