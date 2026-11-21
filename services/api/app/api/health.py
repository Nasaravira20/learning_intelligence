import logging

from fastapi import APIRouter

from app.core.errors import error_response
from app.core.logging import log_event
from app.db.session import ping_database

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str] | object:
    try:
        ping_database()
    except Exception as exc:
        log_event(logger, logging.ERROR, "health_check_failed", error_type=type(exc).__name__)
        logger.exception("health_check_exception")
        return error_response("database_unavailable", "The database is unavailable.", 503)
    return {"status": "ok", "database": "ok"}
