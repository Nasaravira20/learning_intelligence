import asyncio

import httpx
import pytest

from app.core.errors import AppError
from app.core.middleware import MAX_BODY_BYTES, BodySizeLimitMiddleware, RequestContextMiddleware


async def _ok_app(scope, receive, send) -> None:
    if scope["type"] != "http":
        return
    await receive()
    await send({"type": "http.response.start", "status": 204, "headers": []})
    await send({"type": "http.response.body", "body": b""})


def _request(app, method: str, path: str, **kwargs) -> httpx.Response:
    async def scenario() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(scenario())


def test_request_id_is_preserved() -> None:
    app = RequestContextMiddleware(BodySizeLimitMiddleware(_ok_app))
    response = _request(app, "GET", "/", headers={"X-Request-ID": "req-123"})
    assert response.status_code == 204
    assert response.headers["x-request-id"] == "req-123"


def test_oversized_request_id_is_replaced() -> None:
    app = RequestContextMiddleware(_ok_app)
    response = _request(app, "GET", "/", headers={"X-Request-ID": "x" * 200})
    assert response.status_code == 204
    assert response.headers["x-request-id"] != "x" * 200
    assert len(response.headers["x-request-id"]) == 36


def test_declared_body_over_limit_returns_json() -> None:
    app = RequestContextMiddleware(BodySizeLimitMiddleware(_ok_app))
    payload = b"x" * (MAX_BODY_BYTES + 1)
    response = _request(
        app,
        "POST",
        "/api/learners",
        content=payload,
        headers={"X-Request-ID": "req-large", "content-type": "application/json"},
    )
    body = response.json()
    assert response.status_code == 413
    assert body["error"]["code"] == "payload_too_large"
    assert body["error"]["request_id"] == "req-large"
    assert response.headers["x-request-id"] == "req-large"
    assert "x" * 20 not in response.text


def test_streamed_body_over_limit_raises() -> None:
    async def scenario() -> None:
        app = BodySizeLimitMiddleware(_ok_app)

        async def receive():
            return {
                "type": "http.request",
                "body": b"a" * (MAX_BODY_BYTES + 1),
                "more_body": False,
            }

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/learners",
            "raw_path": b"/api/learners",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 123),
            "server": ("test", 80),
        }

        async def send(message) -> None:
            return None

        with pytest.raises(AppError) as caught:
            await app(scope, receive, send)
        assert caught.value.status_code == 413
        assert caught.value.code == "payload_too_large"

    asyncio.run(scenario())
