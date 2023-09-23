import hmac
import logging.config
import os
from dataclasses import dataclass, field
from functools import partial
from hashlib import sha256
from typing import Any, Callable, Final, Optional, TypeVar

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel  # pylint: disable=no-name-in-module

APP_JSON = "application/json"
APP_V1_JSON = "application/vnd.mesh.v1+json"
APP_V2_JSON = "application/vnd.mesh.v2+json"
MAX_API_VERSION = 2

MESH_MEDIA_TYPES: Final[dict[int, str]] = {1: APP_JSON, 2: APP_V2_JSON}


exclude_none_json_encoder = partial(jsonable_encoder, exclude_none=True)


MESH_AUTH_SCHEME = "NHSMESH"


def generate_cipher_text(
    secret_key: str, mailbox_id: str, mailbox_password: str, timestamp: str, nonce: str, nonce_count: str
) -> str:
    private_auth_data = f"{mailbox_id}:{nonce}:{nonce_count}:{mailbox_password}:{timestamp}"

    return hmac.HMAC(str.encode(secret_key), private_auth_data.encode("ASCII"), sha256).hexdigest()


def strtobool(val: Any) -> Optional[bool]:
    if isinstance(val, bool):
        return val
    val = str(val).lower().strip()

    if val in ("y", "yes", "t", "true", "on", "1"):
        return True

    if val in ("n", "no", "f", "false", "off", "0"):
        return False

    return None


@dataclass
class EnvConfig:
    env: str = field(default="local")
    build_label: str = field(default="latest")
    auth_mode: str = field(default="no_auth")
    store_mode: str = field(default="canned")
    shared_key: str = field(default="Banana")
    mailboxes_dir: str = field(default="/tmp/mesh_store")
    message_expiry_days: int = field(default=30)
    inbox_expiry_days: int = field(default=5)

    def __post_init__(self):
        self.env = os.environ.get("ENV", self.env)
        self.build_label = os.environ.get("BUILD_LABEL", self.build_label)
        self.auth_mode = os.environ.get("AUTH_MODE", self.auth_mode)
        self.store_mode = os.environ.get("STORE_MODE", self.store_mode)
        self.shared_key = os.environ.get("SHARED_KEY", self.shared_key)
        self.mailboxes_dir = os.environ.get("MAILBOXES_DATA_DIR", os.environ.get("FILE_STORE_DIR", self.mailboxes_dir))
        self.message_expiry_days = int(os.environ.get("MESSAGE_EXPIRY_DAYS", self.message_expiry_days))
        self.inbox_expiry_days = int(os.environ.get("INBOX_EXPIRY_DAYS", self.inbox_expiry_days))


T = TypeVar("T")


def index_of(items: list[T], find: Callable[[T], bool]) -> int:
    for index, elem in enumerate(items):
        if find(elem):
            return index

    return -1


class LogConfig(BaseModel):
    """Logging configuration to be set for the server"""

    LOGGER_NAME: str = "mesh-sandbox"
    LOG_FORMAT: str = "%(levelprefix)s | %(asctime)s | %(message)s"
    LOG_LEVEL: str = "DEBUG"

    # Logging config
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: dict = {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }
    handlers: dict = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    }
    loggers: dict = {
        "mesh-sandbox": {"handlers": ["default"], "level": LOG_LEVEL},
    }


logging.config.dictConfig(LogConfig().dict())
logger = logging.getLogger("mesh-sandbox")
