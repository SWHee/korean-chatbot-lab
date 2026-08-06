FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.15 /uv /uvx /bin/

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable --no-install-project

COPY src ./src
COPY scripts ./scripts
COPY data/laws ./data/laws
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

EXPOSE 8000

CMD ["fastapi", "run", "--host", "0.0.0.0", "--port", "8000"]
