from __future__ import annotations

import json
import logging
import time
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import AppError, error_payload
from app.core.logging import log_event
from app.core.request_context import reset_request_id, set_request_id, store_request_id

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 64 * 1024
MAX_REQUEST_ID_LENGTH = 128


def _header(scope: Scope, name: str) -> str | None:
    target = name.lower().encode()
    for key, value in scope.get("headers", []):
        if key.lower() == target:
            return value.decode()
    return None


def _clean_request_id(raw: str | None) -> str:
    if raw is None:
        return str(uuid4())
    candidate = raw.strip()
    if not candidate or len(candidate) > MAX_REQUEST_ID_LENGTH:
        return str(uuid4())
    if any(ord(character) < 32 or ord(character) == 127 for character in candidate):
        return str(uuid4())
    return candidate


async def _send_json(send: Send, status: int, payload: dict[str, object]) -> None:
    body = json.dumps(payload).encode()
    request_id = str(payload.get("error", {}).get("request_id", "-")) if isinstance(payload.get("error"), dict) else "-"
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode()),
        (b"x-request-id", request_id.encode()),
    ]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _clean_request_id(_header(scope, "x-request-id"))
        store_request_id(scope, request_id)
        token = set_request_id(request_id)
        started = time.perf_counter()
        status_code = 500
        method = str(scope.get("method", ""))
        path = str(scope.get("path", ""))

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = MutableHeaders(raw=message.setdefault("headers", []))
                headers["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            log_event(
                logger,
                logging.ERROR,
                "request_failed",
                method=method,
                path=path,
                error_type="unhandled",
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            level = logging.ERROR if status_code >= 500 else logging.INFO
            log_event(
                logger,
                level,
                "request_completed",
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
            )
            reset_request_id(token)


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method", "")).upper()
        if method in {"GET", "HEAD", "OPTIONS"}:
            await self.app(scope, receive, send)
            return

        content_length = _header(scope, "content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                log_event(logger, logging.WARNING, "invalid_content_length", path=scope.get("path"))
                await _send_json(
                    send,
                    400,
                    error_payload("bad_request", "The content length was invalid."),
                )
                return
            if declared > self.max_bytes:
                log_event(
                    logger,
                    logging.WARNING,
                    "payload_too_large",
                    path=scope.get("path"),
                    content_length=declared,
                )
                await _send_json(
                    send,
                    413,
                    error_payload("payload_too_large", "The request body is too large."),
                )
                return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                received += len(body)
                if received > self.max_bytes:
                    log_event(logger, logging.WARNING, "payload_too_large", path=scope.get("path"))
                    raise AppError("payload_too_large", "The request body is too large.", 413)
            return message

        await self.app(scope, limited_receive, send)
