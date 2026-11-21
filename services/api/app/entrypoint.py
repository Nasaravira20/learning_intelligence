from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config
from pydantic import ValidationError

from app.core.config import get_settings, safe_database_target
from app.core.logging import configure_logging, log_event
from app.db.session import ping_database

logger = logging.getLogger(__name__)


def _configuration_error(exc: ValidationError) -> None:
    missing = sorted({str(error["loc"][0]) for error in exc.errors() if error.get("loc")})
    sys.stderr.write(json.dumps({"message": "configuration_error", "missing": missing}) + "\n")


def wait_for_database(attempts: int = 30, delay_seconds: float = 1.0) -> None:
    for attempt in range(1, attempts + 1):
        try:
            ping_database()
        except Exception as exc:
            log_event(
                logger,
                logging.WARNING,
                "database_not_ready",
                attempt=attempt,
                error_type=type(exc).__name__,
            )
            if attempt == attempts:
                log_event(logger, logging.ERROR, "database_unavailable", attempts=attempts)
                raise SystemExit(1) from exc
            time.sleep(delay_seconds)
        else:
            log_event(logger, logging.INFO, "database_ready", attempt=attempt)
            return


def apply_migrations() -> None:
    config_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    command.upgrade(Config(str(config_path)), "head")
    log_event(logger, logging.INFO, "migrations_applied")


def main() -> None:
    try:
        settings = get_settings()
    except ValidationError as exc:
        _configuration_error(exc)
        raise SystemExit(1) from exc

    configure_logging(settings.log_level)
    log_event(logger, logging.INFO, "boot", **safe_database_target(settings.database_url))
    try:
        wait_for_database()
        apply_migrations()
    except SystemExit:
        raise
    except Exception as exc:
        log_event(logger, logging.ERROR, "startup_failed", error_type=type(exc).__name__)
        logger.exception("startup_exception")
        raise SystemExit(1) from exc

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
