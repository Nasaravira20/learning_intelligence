FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY services/api/pyproject.toml services/api/alembic.ini ./
COPY services/api/app ./app
RUN pip install --no-cache-dir ".[dev]"

COPY research ./research
COPY services/api/alembic ./alembic
COPY services/api/scripts ./scripts
COPY services/api/tests ./tests

EXPOSE 8000

CMD ["python", "-m", "app.entrypoint"]
