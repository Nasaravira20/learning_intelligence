from app.ai.errors import ProviderError

RETRYABLE = {"timeout", "network", "rate_limit", "unavailable"}


def retryable(error_class: str) -> bool:
    return error_class in RETRYABLE


def classify_api_failure(status_code: int | None, error_code: str, message: str) -> str:
    blob = f"{error_code} {message}".lower()
    if status_code == 401 or "api key" in blob or "api_key_invalid" in blob or "authentication" in blob:
        return "invalid_key"
    if status_code == 403 or "permission" in blob:
        return "permission"
    if "quota" in blob or "resource_exhausted" in blob or status_code == 402 or "payment_required" in blob:
        return "quota"
    if status_code == 429 or "rate_limit" in blob or "rate limit" in blob or "too many requests" in blob:
        return "rate_limit"
    if "not supported" in blob or "unsupported" in blob or "unimplemented" in blob or status_code == 501:
        return "unsupported_operation"
    if status_code == 404 or "not_found" in blob or "not found" in blob or "no longer available" in blob:
        return "model_not_found"
    if status_code == 504 or "deadline" in blob or "timeout" in blob:
        return "timeout"
    if status_code in {500, 503}:
        return "unavailable"
    return "unknown"


def classify_exception(exc: BaseException) -> str:
    type_name = type(exc).__name__.lower()
    if type_name in {
        "timeoutexception",
        "timeouterror",
        "readtimeout",
        "connecttimeout",
        "writetimeout",
        "continuationinterruptederror",
    }:
        return "timeout"
    if type_name in {"connecterror", "connectionerror", "networkerror", "remoteprotocolerror"}:
        return "network"
    status_code = getattr(exc, "code", None)
    if not isinstance(status_code, int):
        status_code = None
    error_code = str(getattr(exc, "status", "") or "")
    details = getattr(exc, "details", None)
    if isinstance(details, dict):
        nested = details.get("error", details)
        if isinstance(nested, dict):
            error_code = f"{error_code} {nested.get('code') or ''}"
    message = str(getattr(exc, "message", "") or exc)
    return classify_api_failure(status_code, error_code, message)


def provider_error_from_exception(exc: BaseException) -> ProviderError:
    error_class = classify_exception(exc)
    return ProviderError(error_class, retryable(error_class))
