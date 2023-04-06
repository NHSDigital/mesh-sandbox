MESH Sandbox
===========

MESH sandbox for local testing of [NHS Digital's MESH API](https://digital.nhs.uk/developer/api-catalogue/message-exchange-for-social-care-and-health-api).

Installation
------------

Example use
-----------

pip
---

```bash
pip install mesh-sandbox
STORE_MODE=file MAILBOXES_DATA_DIR=/tmp/mesh uvicorn mesh_sandbox.api:app --reload --port 8700 --workers=1
curl http://localhost:8700/health
```

docker compose
--------------

```yaml
version: '3.9'


services:

  mesh_sandbox:
    build: 
      context: https://github.com/NHSDigital/mesh-sandbox.git#develop
    ports:
      - "8700:80"
    deploy:
      restart_policy:
        condition: on-failure
        max_attempts: 3
    healthcheck:
      test: curl -sf http://localhost:80/health || exit 1
      interval: 3s
      timeout: 10s
    environment:
      - SHARED_KEY=TestKey
    volumes:
      # mount a different mailboxes.jsonl to pre created mailboxes
      - ./src/mesh_sandbox/store/data/mailboxes.jsonl:/app/mesh_sandbox/store/data/mailboxes.jsonl:ro

```

Guidance for contributors
-------------------------

this project uses

- python 3.9
- java coretto11
- poetry > 1.2

Setup
-----

using asdf
[install asdf](https://asdf-vm.com/guide/getting-started.html#_3-install-asdf)

get the required plugins

```bash
asdf plugin add python
asdf plugin add java
asdf plugin add poetry
```

install the tools

```bash
asdf install
```

install the dependencies

```bash
make install
```
