# Django API. The build context is the repository root so the uv workspace
# member in backend/packages/ is available alongside the lockfile.
FROM python:3.14-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first: editing api/ or config/ must not reinstall Django.
# The workspace member is copied with them because it is one of them.
COPY backend/pyproject.toml backend/uv.lock ./
COPY backend/packages ./packages
RUN uv sync --locked --no-dev

COPY backend/manage.py ./
COPY backend/config ./config
COPY backend/api ./api

COPY docker/backend-entrypoint.sh /usr/local/bin/backend-entrypoint
RUN chmod +x /usr/local/bin/backend-entrypoint

EXPOSE 8000
ENTRYPOINT ["backend-entrypoint"]
