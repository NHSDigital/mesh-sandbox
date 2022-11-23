FROM python:3.9

WORKDIR /app

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt \
    && mkdir -p /tmp/mesh_store

COPY src/mesh_sandbox /app/mesh_sandbox

ENV AUTH_MODE=full
ENV STORE_MODE=file
ENV FILE_STORE_DIR=/tmp/mesh_store
ENV SHARED_KEY=TestKey

CMD ["uvicorn", "mesh_sandbox.api:app", "--host", "0.0.0.0", "--port", "80", "--workers", "1"]
