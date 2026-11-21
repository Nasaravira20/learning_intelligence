FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml alembic.ini ./
COPY app ./app
RUN pip install --no-cache-dir ".[dev]"

COPY alembic ./alembic
COPY scripts ./scripts
COPY tests ./tests

EXPOSE 8000

CMD ["python", "-m", "app.entrypoint"]
