from __future__ import annotations

import json
import logging
import re
import sys
import traceback
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.core.request_context import get_request_id

SENSITIVE_KEY_PARTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "authorization",
    "database_url",
    "cookie",
)

USERINFO = re.compile(r"://[^/\s:]+:[^/\s@]+@")
CONNECTION_URL = re.compile(r"postgresql(?:\+\w+)?://\S+", re.IGNORECASE)
BEARER = re.compile(r"(?i)bearer\s+\S+")
GOOGLE_KEY = re.compile(r"AIza[0-9A-Za-z\-_]{20,}")
QUERY_SECRET = re.compile(
    r"(?i)(token|api_key|password|secret|authorization)=([^&\s]+)"
)


def redact_text(value: str) -> str:
    redacted = USERINFO.sub("://[redacted]@", value)
    redacted = CONNECTION_URL.sub("postgresql://[redacted]", redacted)
    redacted = BEARER.sub("Bearer [redacted]", redacted)
    redacted = GOOGLE_KEY.sub("[redacted]", redacted)
    redacted = QUERY_SECRET.sub(r"\1=[redacted]", redacted)
    return redacted


def _is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def redact_fields(fields: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in fields.items():
        if _is_sensitive(key):
            cleaned[key] = "[redacted]"
        else:
            cleaned[key] = normalize(value)
    return cleaned


def normalize(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return redact_fields(value)
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return redact_text(str(value))


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = getattr(record, "request_id", None) or get_request_id() or "-"
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(redact_text(item) if isinstance(item, str) else item for item in record.args)
        elif isinstance(record.args, dict):
            record.args = {
                key: redact_text(value) if isinstance(value, str) else value
                for key, value in record.args.items()
            }
        if record.exc_info and not record.exc_text:
            record.exc_text = redact_text("".join(traceback.format_exception(*record.exc_info)).rstrip())
        elif isinstance(record.exc_text, str):
            record.exc_text = redact_text(record.exc_text)
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
            "request_id": getattr(record, "request_id", "-"),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict) and fields:
            payload["fields"] = redact_fields(fields)
        if record.exc_info:
            payload["exception"] = redact_text(
                "".join(traceback.format_exception(*record.exc_info)).rstrip()
            )
        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.filters.clear()
    root.addFilter(RequestIdFilter())
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())
    root.addHandler(handler)
    root.setLevel(level.upper())

    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("uvicorn.error").setLevel(level.upper())
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.INFO)


def log_event(logger: logging.Logger, level: int, message: str, **fields: Any) -> None:
    logger.log(level, message, extra={"fields": fields})
