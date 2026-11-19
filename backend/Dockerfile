# SAPS API and SAPS Worker share this image (ADR-0004); the command selects the container role.
FROM ghcr.io/astral-sh/uv:0.9.18 AS uv

FROM python:3.14-slim AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.14-slim
RUN useradd --create-home --uid 10001 saps
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY alembic.ini ./
COPY migrations ./migrations
COPY fixtures ./fixtures
ENV PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1
USER saps
EXPOSE 8000
# SAPS API: migrate, seed demo data (skipped without SEED_USER_PASSWORD), then serve.
# The SAPS Worker overrides the command in compose.yaml.
CMD ["sh", "-c", "alembic upgrade head && python -m saps.seed && uvicorn saps.api.main:app --host 0.0.0.0 --port 8000"]
