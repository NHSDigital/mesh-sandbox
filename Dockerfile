FROM python:3.9

WORKDIR /app

COPY ./requirements.txt /requirements.txt

RUN pip install --no-cache-dir --upgrade -r /requirements.txt \
    && mkdir -p /tmp/mesh_store


COPY entrypoint.sh /entrypoint.sh
COPY src/mesh_sandbox /app/mesh_sandbox

ENV AUTH_MODE=full
ENV STORE_MODE=file
ENV FILE_STORE_DIR=/tmp/mesh_store
ENV SHARED_KEY=TestKey

CMD ["/bin/bash", "/entrypoint.sh"]
