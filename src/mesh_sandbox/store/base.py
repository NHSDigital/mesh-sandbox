from abc import ABC, abstractmethod
from typing import NamedTuple, Optional

from fastapi import HTTPException, status

from ..common import EnvConfig, constants, generate_cipher_text
from ..models.mailbox import Mailbox
from ..models.message import Message


class AuthoriseHeaderParts(NamedTuple):
    scheme: str
    mailbox_id: str
    nonce: str
    nonce_count: str
    timestamp: str
    cipher_text: str
    parts: int

    def get_reasons_invalid(self) -> list[str]:
        reasons = []
        if self.parts != 5:
            reasons.append(f"invalid num header parts: {self.parts}")

        if not self.nonce_count.isdigit():
            reasons.append("nonce count is not digits")

        if self.scheme not in (MESH_AUTH_SCHEME, ""):
            reasons.append("invalid auth scheme or mailbox_id contains a space")

        if " " in self.mailbox_id:
            reasons.append("mailbox_id contains a space")

        return reasons


_DEFAULT_PARTS_IF_MISSING = ["" for _ in range(5)]
MESH_AUTH_SCHEME = "NHSMESH"


def try_parse_authorisation_token(auth_token: str) -> Optional[AuthoriseHeaderParts]:

    if not auth_token:
        return None

    auth_token = auth_token.strip()

    scheme = MESH_AUTH_SCHEME if auth_token.upper().startswith(MESH_AUTH_SCHEME) else ""

    if scheme:
        auth_token = auth_token[len(MESH_AUTH_SCHEME) + 1 :]

    auth_token_parts = auth_token.split(":")

    num_parts = len(auth_token_parts)
    auth_token_parts = auth_token_parts + _DEFAULT_PARTS_IF_MISSING

    header_parts = AuthoriseHeaderParts(
        scheme=scheme,
        mailbox_id=auth_token_parts[0],
        nonce=auth_token_parts[1],
        nonce_count=auth_token_parts[2],
        timestamp=auth_token_parts[3],
        cipher_text=auth_token_parts[4],
        parts=num_parts,
    )

    return header_parts


class Store(ABC):
    def __init__(self, config: EnvConfig):
        self.config = config

    @abstractmethod
    async def get_mailbox(self, mailbox_id: str, accessed: bool = False) -> Optional[Mailbox]:
        pass

    async def _validate_auth_token(self, mailbox_id: str, authorization: str) -> Optional[Mailbox]:

        if self.config.auth_mode == "none":
            return await self.get_mailbox(mailbox_id, accessed=True)

        authorization = (authorization or "").strip()
        if not authorization:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=constants.ERROR_READING_AUTH_HEADER)

        header_parts = try_parse_authorisation_token(authorization)
        if not header_parts:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=constants.ERROR_READING_AUTH_HEADER)

        if header_parts.mailbox_id != mailbox_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=constants.ERROR_MAILBOX_TOKEN_MISMATCH)

        if self.config.auth_mode == "canned":

            if header_parts.nonce.upper() != "VALID":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=constants.ERROR_INVALID_AUTH_TOKEN)
            return await self.get_mailbox(mailbox_id, accessed=True)

        if header_parts.get_reasons_invalid():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=constants.ERROR_INVALID_AUTH_TOKEN)

        mailbox = await self.get_mailbox(mailbox_id, accessed=True)

        if not mailbox:
            return None

        cypher_text = generate_cipher_text(
            self.config.shared_key,
            header_parts.mailbox_id,
            mailbox.password,
            header_parts.timestamp,
            header_parts.nonce,
            header_parts.nonce_count,
        )

        if header_parts.cipher_text != cypher_text:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=constants.ERROR_INVALID_AUTH_TOKEN)

        return mailbox

    async def authorise_mailbox(self, mailbox_id: str, authorization: str) -> Optional[Mailbox]:

        mailbox = await self._validate_auth_token(mailbox_id, authorization)

        if not mailbox:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=constants.ERROR_NO_MAILBOX_MATCHES)

        return mailbox

    @abstractmethod
    async def send_message(self, message: Message, body: bytes):
        pass

    @abstractmethod
    async def receive_chunk(self, message: Message, chunk_number: int, chunk: bytes):
        pass

    @abstractmethod
    async def accept_message(self, message: Message):
        pass

    @abstractmethod
    async def acknowledge_message(self, message: Message):
        pass

    @abstractmethod
    async def get_message(self, message_id: str) -> Optional[Message]:
        pass

    @abstractmethod
    async def get_inbox(self, mailbox_id: str) -> list[Message]:
        pass

    @abstractmethod
    async def get_outbox(self, mailbox_id: str) -> list[Message]:
        pass

    @abstractmethod
    async def get_by_local_id(self, mailbox_id: str, local_id: str) -> list[Message]:
        pass

    @abstractmethod
    async def retrieve_chunk(self, message: Message, chunk_number: int) -> Optional[bytes]:
        pass

    @abstractmethod
    async def lookup_by_ods_code_and_workflow_id(self, ods_code: str, workflow_id: str) -> list[Mailbox]:
        pass

    @abstractmethod
    async def lookup_by_workflow_id(self, workflow_id: str) -> list[Mailbox]:
        pass
