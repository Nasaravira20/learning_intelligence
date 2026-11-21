from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.api import auth, diagnostics, health, learner, learners, pedagogy, planning, sessions, teaching, topics
from app.core.config import get_settings, safe_database_target
from app.core.errors import AppError, error_response
from app.core.logging import configure_logging, log_event
from app.core.request_context import use_request_id
from app.core.middleware import BodySizeLimitMiddleware, RequestContextMiddleware
from app.db.errors import constraint_name, sqlstate, translate_integrity_error
from app.db.session import ping_database

logger = logging.getLogger(__name__)


def _field_name(location: tuple[object, ...]) -> str:
    parts = [str(part) for part in location if part not in {"body", "query", "path"}]
    return ".".join(parts) or "request"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    log_event(
        logger,
        logging.INFO,
        "application_starting",
        app=settings.app_name,
        version=__version__,
        **safe_database_target(settings.database_url),
    )
    try:
        ping_database()
    except Exception as exc:
        log_event(logger, logging.ERROR, "database_check_failed", error_type=type(exc).__name__)
        logger.exception("database_check_exception")
    else:
        log_event(logger, logging.INFO, "database_check_passed")
    yield
    log_event(logger, logging.INFO, "application_stopping")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan, debug=False)
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware)
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api")
    app.include_router(learners.router, prefix="/api")
    app.include_router(topics.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")
    app.include_router(learner.router, prefix="/api")
    app.include_router(diagnostics.topics, prefix="/api")
    app.include_router(diagnostics.sessions, prefix="/api")
    app.include_router(planning.topics, prefix="/api")
    app.include_router(planning.sessions, prefix="/api")
    app.include_router(pedagogy.router, prefix="/api")
    app.include_router(pedagogy.sessions, prefix="/api")
    app.include_router(teaching.sessions, prefix="/api")
    _register_exception_handlers(app)
    return app


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        with use_request_id(request.scope):
            level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
            log_event(
                logger,
                level,
                "application_error",
                code=exc.code,
                status_code=exc.status_code,
                path=request.url.path,
            )
            return error_response(exc.code, exc.message, exc.status_code, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        with use_request_id(request.scope):
            details = [
                {
                    "field": _field_name(tuple(error.get("loc", ()))),
                    "message": str(error.get("msg", "Invalid value.")),
                }
                for error in exc.errors()
            ]
            log_event(
                logger,
                logging.WARNING,
                "validation_failed",
                path=request.url.path,
                fields_invalid=[item["field"] for item in details],
            )
            return error_response("validation_error", "The request was invalid.", 422, details)

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError):
        with use_request_id(request.scope):
            translated = translate_integrity_error(exc)
            log_event(
                logger,
                logging.WARNING,
                "integrity_error",
                path=request.url.path,
                code=translated.code,
                sqlstate=sqlstate(exc),
                constraint=constraint_name(exc),
            )
            return error_response(translated.code, translated.message, translated.status_code)

    @app.exception_handler(OperationalError)
    async def handle_operational_error(request: Request, exc: OperationalError):
        with use_request_id(request.scope):
            log_event(
                logger,
                logging.ERROR,
                "database_error",
                path=request.url.path,
                error_type=type(exc).__name__,
            )
            logger.exception("database_exception")
            return error_response("database_unavailable", "The database is unavailable.", 503)

    @app.exception_handler(DBAPIError)
    async def handle_dbapi_error(request: Request, exc: DBAPIError):
        with use_request_id(request.scope):
            log_event(
                logger,
                logging.ERROR,
                "database_error",
                path=request.url.path,
                error_type=type(exc).__name__,
            )
            logger.exception("database_exception")
            return error_response("database_unavailable", "The database is unavailable.", 503)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        with use_request_id(request.scope):
            code = {
                400: "bad_request",
                404: "not_found",
                405: "method_not_allowed",
            }.get(exc.status_code, "http_error")
            message = exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
            level = logging.ERROR if exc.status_code >= 500 else logging.INFO
            log_event(
                logger,
                level,
                "http_error",
                path=request.url.path,
                code=code,
                status_code=exc.status_code,
            )
            return error_response(code, message, exc.status_code)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        with use_request_id(request.scope):
            log_event(
                logger,
                logging.ERROR,
                "unhandled_error",
                path=request.url.path,
                error_type=type(exc).__name__,
            )
            logger.exception("unhandled_exception")
            return error_response("internal_error", "The request could not be completed.", 500)


app = create_app()
