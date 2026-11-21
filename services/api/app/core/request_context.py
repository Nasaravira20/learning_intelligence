from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return _request_id.get()


def set_request_id(request_id: str) -> Token[str | None]:
    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    _request_id.reset(token)


def store_request_id(scope: dict[str, Any], request_id: str) -> None:
    state = scope.get("state")
    if state is None:
        scope["state"] = {"request_id": request_id}
        return
    if isinstance(state, dict):
        state["request_id"] = request_id
        return
    setattr(state, "request_id", request_id)


def request_id_from_scope(scope: dict[str, Any]) -> str | None:
    state = scope.get("state")
    value = state.get("request_id") if isinstance(state, dict) else getattr(state, "request_id", None)
    if isinstance(value, str) and value.strip():
        return value
    return None


@contextmanager
def use_request_id(scope: dict[str, Any]) -> Iterator[str]:
    current = get_request_id()
    token: Token[str | None] | None = None
    if current is None:
        found = request_id_from_scope(scope)
        if found:
            token = set_request_id(found)
            current = found
    try:
        yield current or "-"
    finally:
        if token is not None:
            reset_request_id(token)
