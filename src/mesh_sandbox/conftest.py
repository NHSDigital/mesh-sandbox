import pytest
from fastapi.testclient import TestClient

from .api import app
from .dependencies import get_env_config, get_store
from .tests.helpers import temp_env_vars


@pytest.fixture(scope="function", autouse=True)
def setup():

    get_store.cache_clear()
    get_env_config.cache_clear()

    with temp_env_vars(
        ENV="local",
        BUILD_LABEL="test",
        AUTH_MODE="full",
        STORE_MODE="memory",
        SHARED_KEY="TestKey",
    ):
        yield


@pytest.fixture(scope="function", name="app")
def test_app() -> TestClient:

    return TestClient(app)
