from sqlalchemy.exc import IntegrityError

from app.core.errors import AppError, ConflictError, NotFoundError


def sqlstate(exc: IntegrityError) -> str | None:
    return getattr(exc.orig, "sqlstate", None)


def constraint_name(exc: IntegrityError) -> str | None:
    diagnosis = getattr(exc.orig, "diag", None)
    return getattr(diagnosis, "constraint_name", None)


def translate_integrity_error(exc: IntegrityError) -> AppError:
    state = sqlstate(exc)
    name = constraint_name(exc) or ""
    if state == "23505":
        if "slug" in name:
            return ConflictError("topic_slug_taken", "A topic with this slug already exists.")
        if "email" in name:
            return ConflictError("email_taken", "An account with this email already exists.")
        return ConflictError("conflict", "The record already exists.")
    if state == "23503":
        return NotFoundError("related_record_missing", "A related learner or topic was not found.")
    if state == "23514":
        return AppError("validation_error", "The request was invalid.", 422)
    return AppError("constraint_violation", "The request could not be saved.", 409)
