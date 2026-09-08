FROM python:3.11.16-slim-bookworm@sha256:528257d48c1da0dcecc2e725d1ae34498d60c965f1241e39cd6a85a8859bdf84

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN apt-get update \
    && apt-get install curl -yq --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --only-binary :all: poetry==2.1.2 \
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
