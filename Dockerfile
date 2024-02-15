FROM python:3.9-slim-bullseye@sha256:cb47448b7dd1bf0895916c1defab259ed795cb0b531487156c5499298dc3dc8b

WORKDIR /app

COPY ./requirements.txt /requirements.txt

RUN apt-get update && echo "j" \
    && apt-get install curl -yq --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade -r /requirements.txt \
    && mkdir -p /tmp/mesh_store


COPY entrypoint.sh /entrypoint.sh
COPY src/mesh_sandbox /app/mesh_sandbox

ENV AUTH_MODE=full
ENV STORE_MODE=file
ENV FILE_STORE_DIR=/tmp/mesh_store
ENV SHARED_KEY=TestKey

CMD ["/bin/bash", "/entrypoint.sh"]
