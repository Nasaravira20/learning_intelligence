"""Verify Gemini models with the configured key. Never prints the key."""

import os
from pathlib import Path

from app.ai.providers.gemini import GeminiProvider
from app.ai.verification import configuration_problem, run_verification
from app.core.config import get_settings
from app.db.session import get_sessionmaker


def main() -> int:
    problem = configuration_problem()
    if problem:
        print(problem)
        return 2
    settings = get_settings()
    provider = GeminiProvider(settings.gemini_api_key or "", settings.gemini_timeout_seconds)
    strategy_path = Path(os.environ.get("MODEL_STRATEGY_PATH", "docs/GEMINI_MODEL_STRATEGY.md"))
    session = get_sessionmaker()()
    try:
        code = run_verification(session, provider, strategy_path)
        session.commit()
    except Exception as exc:
        session.rollback()
        print(f"Model verification failed: {type(exc).__name__}")
        return 1
    finally:
        session.close()
    print(f"Wrote the model strategy report. Exit {code}.")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
