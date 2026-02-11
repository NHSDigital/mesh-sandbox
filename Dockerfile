FROM python:3.11-slim-bullseye@sha256:53ebfd268fe58ccd405688b3305a7dcad5da03f5e3957126a40c9e59d0962ed0

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN apt-get update \
    && apt-get install curl -yq --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root \
    && mkdir -p /tmp/mesh_store


COPY entrypoint.sh /entrypoint.sh
COPY src/mesh_sandbox /app/mesh_sandbox

ENV AUTH_MODE=full
ENV STORE_MODE=file
ENV FILE_STORE_DIR=/tmp/mesh_store
ENV SHARED_KEY=TestKey

CMD ["/bin/bash", "/entrypoint.sh"]
