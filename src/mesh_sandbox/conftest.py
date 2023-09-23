import asyncio
import os
from threading import Thread
from time import sleep, time
from typing import Callable, Optional

import httpx
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from uvicorn import Config, Server  # type: ignore[import]

from .api import app
from .dependencies import get_env_config, get_messaging, get_store
from .tests.helpers import temp_env_vars


@pytest.fixture(autouse=True)
def setup():
    get_store.cache_clear()
    get_env_config.cache_clear()
    get_messaging.cache_clear()

    with temp_env_vars(
        ENV="local",
        BUILD_LABEL="test",
        AUTH_MODE="full",
        STORE_MODE="memory",
        SHARED_KEY="TestKey",
    ):
        yield


@pytest.fixture(name="app")
def test_app() -> TestClient:
    return TestClient(app)


class StoppableServer:
    def __init__(self, port: int):
        self.port = port
        self._config = Config(app, port=self.port, workers=1)
        self.server: Optional[Server] = None

    def run(self):
        self.server = Server(config=self._config)
        asyncio.run(self.server.serve())

    def stop(self):
        if not self.server:
            return
        self.server.should_exit = True
        if self._config.uds:
            os.remove(self._config.uds)


@pytest.fixture(scope="session", name="base_uri")
def create_server(unused_tcp_port_factory: Callable[[], int]):
    port = unused_tcp_port_factory()

    server = StoppableServer(port)

    server_thread = Thread(target=server.run)
    server_thread.start()
    try:
        base_uri = f"http://localhost:{port}"
        timeout = time() + 1
        with httpx.Client(base_url=base_uri) as client:
            while True:
                try:
                    res = client.get("/health")
                    if res.status_code == status.HTTP_200_OK:
                        break
                    raise ValueError(res.status_code)
                except httpx.ConnectError:
                    sleep(0.1)
                    if time() > timeout:
                        break
                    continue

        yield base_uri
    finally:
        server.stop()
        server_thread.join()
