# syntax=docker/dockerfile:experimental

FROM python:3.12-slim-bookworm as build
COPY --from=ghcr.io/astral-sh/uv:0.7.22 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0 UV_INDEX_PRIVATE_REGISTRY_USERNAME=aws

RUN apt-get update; apt-get install -y --no-install-recommends git libpq-dev build-essential

WORKDIR /code
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=secret,id=UV_INDEX_PRIVATE_REGISTRY_PASSWORD \
    UV_INDEX_PRIVATE_REGISTRY_PASSWORD=$(cat /run/secrets/UV_INDEX_PRIVATE_REGISTRY_PASSWORD) \
    uv sync --locked --no-install-project --no-dev --keyring-provider disabled -v
COPY . /code
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=secret,id=UV_INDEX_PRIVATE_REGISTRY_PASSWORD \
    UV_INDEX_PRIVATE_REGISTRY_PASSWORD=$(cat /run/secrets/UV_INDEX_PRIVATE_REGISTRY_PASSWORD) \
    uv sync --locked --no-dev --group aws --keyring-provider disabled -v
RUN chmod a+x /code/docker-entrypoint.sh

FROM python:3.12-slim-bookworm
RUN apt-get update; apt-get install -y --no-install-recommends git libpq5
COPY --from=build /code /code
ENV PATH="/code/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED 1
WORKDIR /code
ENTRYPOINT ["/code/docker-entrypoint.sh"]
EXPOSE 8000
