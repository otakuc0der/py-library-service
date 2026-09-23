FROM python:3.14-slim

LABEL maintainer="sabina.gamidova.dev@gmail.com"

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

RUN uv sync \
        --frozen \
        --group dev \
        --no-install-project \
    && adduser \
        --disabled-password \
        --no-create-home \
        --gecos "" \
        appuser \
    && mkdir -p \
        /files/media \
        /files/static

COPY . .

RUN chown -R appuser:appuser /app /files \
    && chmod -R 755 /files

USER appuser
