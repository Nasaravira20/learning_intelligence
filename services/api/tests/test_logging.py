import logging
from io import StringIO

from app.core.config import safe_database_target
from app.core.logging import JsonFormatter, RequestIdFilter, configure_logging, log_event, redact_text


def test_safe_database_target_omits_credentials() -> None:
    target = safe_database_target("postgresql+psycopg://ai_teacher:supersecret@db:5432/ai_teacher")
    assert target == {
        "scheme": "postgresql+psycopg",
        "host": "db",
        "port": 5432,
        "database": "ai_teacher",
    }
    assert "supersecret" not in str(target)


def test_redact_text_removes_urls_and_keys() -> None:
    raw = " ".join(
        [
            "postgresql+psycopg://ai_teacher:supersecret@db:5432/ai_teacher",
            "Bearer secret-token",
            "AIzaSyA1234567890abcdefghij",
            "password=hunter2",
        ]
    )
    redacted = redact_text(raw)
    assert "supersecret" not in redacted
    assert "secret-token" not in redacted
    assert "AIzaSyA1234567890abcdefghij" not in redacted
    assert "hunter2" not in redacted
    assert "[redacted]" in redacted


def test_log_event_redacts_sensitive_fields() -> None:
    configure_logging("INFO")
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())
    logging.getLogger().addHandler(handler)
    log_event(
        logging.getLogger("test.redaction"),
        logging.ERROR,
        "failed postgresql+psycopg://ai_teacher:supersecret@db/ai_teacher",
        database_url="postgresql+psycopg://ai_teacher:supersecret@db/ai_teacher",
        host="db",
    )
    try:
        raise RuntimeError("postgresql+psycopg://ai_teacher:supersecret@db/ai_teacher")
    except RuntimeError:
        logging.getLogger("test.redaction").exception("boom")

    output = stream.getvalue()
    assert "supersecret" not in output
    assert "db" in output
    assert "unhandled" not in output or "boom" in output
    assert '"host": "db"' in output or '"host":"db"' in output
