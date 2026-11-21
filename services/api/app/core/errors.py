from __future__ import annotations

from dataclasses import dataclass

from fastapi.responses import JSONResponse

from app.core.request_context import get_request_id


@dataclass
class AppError(Exception):
    code: str
    message: str
    status_code: int
    details: list[dict[str, str]] | None = None

    def __str__(self) -> str:
        return self.message


class NotFoundError(AppError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=404)


class ConflictError(AppError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=409)


def error_payload(
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    error: dict[str, object] = {
        "code": code,
        "message": message,
        "request_id": get_request_id() or "-",
    }
    if details:
        error["details"] = details
    return {"error": error}


def error_response(
    code: str,
    message: str,
    status_code: int,
    details: list[dict[str, str]] | None = None,
) -> JSONResponse:
    response = JSONResponse(
        status_code=status_code,
        content=error_payload(code, message, details),
    )
    request_id = get_request_id()
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response
