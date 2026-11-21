import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

API_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_URL = "postgresql+psycopg://ai_teacher:ai_teacher@localhost:5432/ai_teacher"


def replace_database(url: str, database: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, f"/{database}", parts.query, parts.fragment))


os.environ["DATABASE_URL"] = replace_database(
    os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL),
    "ai_teacher_test",
)
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("WEB_ORIGIN", "http://localhost:3000")


@pytest.fixture(scope="session")
def migrated_database() -> str:
    previous = os.getcwd()
    os.chdir(API_ROOT)
    url = os.environ["DATABASE_URL"]
    admin = create_engine(
        replace_database(url, "postgres"),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
        connect_args={"connect_timeout": 3},
    )
    with admin.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'ai_teacher_test'")
        ).scalar()
        if not exists:
            connection.execute(text("CREATE DATABASE ai_teacher_test"))
    admin.dispose()

    test_engine = create_engine(url, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    with test_engine.connect() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        connection.execute(text("GRANT ALL ON SCHEMA public TO public"))
    test_engine.dispose()

    from alembic import command
    from alembic.config import Config

    from app.core.config import get_settings
    from app.db.session import get_engine, get_sessionmaker

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
    config = Config(str(API_ROOT / "alembic.ini"))
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    try:
        yield url
    finally:
        os.chdir(previous)


@pytest.fixture
def client(migrated_database: str):
    from fastapi.testclient import TestClient

    from app.db.session import get_engine
    from app.main import app

    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE auth_sessions, learning_sessions, learning_topics, learner_profiles, users, "
                "ai_usage_records, ai_model_checks, learning_goals, learning_preferences, "
                "learner_knowledge, misconception_records, assessment_records, learning_activities, "
                "learning_objectives, objective_prerequisites, diagnostic_attempts, "
                "diagnostic_questions, diagnostic_responses "
                "RESTART IDENTITY CASCADE"
            )
        )
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
