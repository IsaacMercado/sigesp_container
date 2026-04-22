FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY faketime_api ./faketime_api
COPY container/faketime/current.rc.example ./container/faketime/current.rc

RUN mkdir -p /app/service_data

EXPOSE 8080

CMD [".venv/bin/python", "-m", "faketime_api", "serve"]