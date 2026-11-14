# Telemetry generator. It only pushes to the backend, so it needs no ports.
FROM python:3.14-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY imitacija/pyproject.toml imitacija/uv.lock imitacija/readme.md ./
COPY imitacija/src ./src
RUN uv sync --locked --no-dev

# Scenarios are data, not code: a new TOML only needs a rebuild of this layer.
COPY imitacija/config ./config

COPY docker/imitacija-entrypoint.sh /usr/local/bin/imitacija-entrypoint
RUN chmod +x /usr/local/bin/imitacija-entrypoint

ENTRYPOINT ["imitacija-entrypoint"]
