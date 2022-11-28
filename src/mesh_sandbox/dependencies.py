import re
from functools import lru_cache
from typing import Optional

from fastapi import Depends, Header, HTTPException, Path, Query, Request

from .common import EnvConfig
from .common.constants import Headers
from .common.fernet import FernetHelper
from .store.base import Store
from .store.canned_store import CannedStore
from .store.file_store import FileStore
from .store.memory_store import MemoryStore

_ACCEPTABLE_ACCEPTS = re.compile(r"^application/vnd\.mesh\.v(\d+)\+json$")


def parse_accept_header(accept: str) -> Optional[int]:

    if not accept:
        return 1

    for accepts in accept.split(";"):
        accepts = accepts.strip()
        if not accepts or "vnd.mesh" not in accepts:
            continue

        match = _ACCEPTABLE_ACCEPTS.match(accepts)
        if not match:
            return None
        accepts_version = int(match.group(1))
        return accepts_version

    return 1


async def get_accepts_api_version(
    accept: str = Header(
        title="Accept",
        default="application/json",
        description="the accepts header can be used to vary the response type",
        example="application/vnd.mesh.v2+json",
    ),
) -> int:
    accepts = parse_accept_header(accept)

    if accepts is None:
        raise HTTPException(status_code=400, detail="Accept header api format incorrect")

    if not accept:
        return 1

    return accepts


async def normalise_mailbox_id_path(
    mailbox_id: str = Path(
        ..., title="mailbox_id", description="mailbox identifier", Example="MAILBOX01", min_length=1
    ),
):
    return mailbox_id.upper()


async def normalise_message_id_path(
    message_id: str = Path(
        ...,
        title="message_id",
        description="message identifier",
        example="20210311101813838554_1B8F53",
        min_length=1,
    ),
):
    return message_id.upper()


async def normalise_message_id_query(
    message_id: str = Query(
        ...,
        alias="messageID",
        title="message identifier",
        description="message identifier",
        example="20210311101813838554_1B8F53",
        min_length=1,
    ),
):
    return message_id.upper()


@lru_cache()
def get_env_config() -> EnvConfig:
    return EnvConfig()


@lru_cache()
def get_store() -> Store:

    config = get_env_config()
    if config.store_mode == "canned":
        return CannedStore(config)

    if config.store_mode == "memory":
        return MemoryStore(config)

    if config.store_mode == "file":
        return FileStore(config)

    raise ValueError(f"unrecognised store mode {config.store_mode}")


@lru_cache()
def get_fernet() -> FernetHelper:
    return FernetHelper()


async def authorised_mailbox(
    request: Request,
    mailbox_id: str = Depends(normalise_mailbox_id_path),
    authorization: str = Header(
        title=Headers.Authorization,
        description="Authorisation header",
        example=(
            "authorization: NHSMESH TEST:2c001608-5f09-4840-9611-bea43e666a30:"
            "1:201511201038:3cded68a9e0f9b83f2c5de1b79fc4dac45004523e6658d46145156fa6a03eced"
        ),
        default="",
    ),
    store: Store = Depends(get_store),
):

    request.state.authorised_mailbox = await store.authorise_mailbox(mailbox_id, authorization)
