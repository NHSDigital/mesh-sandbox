import logging
from abc import ABC, abstractmethod
from typing import Callable, Optional

from ..common import EnvConfig
from ..models.mailbox import Mailbox
from ..models.message import Message


class Store(ABC):
    readonly = True

    def __init__(self, config: EnvConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger

    @abstractmethod
    async def get_mailbox(self, mailbox_id: str, accessed: bool = False) -> Optional[Mailbox]:
        pass

    @abstractmethod
    async def get_message(self, message_id: str) -> Optional[Message]:
        pass

    @abstractmethod
    async def save_message(self, message: Message):
        pass

    @abstractmethod
    async def get_chunk(self, message: Message, chunk_number: int) -> Optional[bytes]:
        pass

    @abstractmethod
    async def save_chunk(self, message: Message, chunk_number: int, chunk: bytes):
        pass

    @abstractmethod
    async def add_to_outbox(self, message: Message):
        pass

    @abstractmethod
    async def add_to_inbox(self, message: Message):
        pass

    @abstractmethod
    async def get_file_size(self, message: Message) -> int:
        pass

    @abstractmethod
    async def reset(self):
        pass

    @abstractmethod
    async def reset_mailbox(self, mailbox_id: str):
        pass

    @abstractmethod
    async def get_inbox_messages(
        self, mailbox_id: str, predicate: Optional[Callable[[Message], bool]] = None
    ) -> list[Message]:
        pass

    @abstractmethod
    async def get_outbox(self, mailbox_id: str) -> list[Message]:
        pass

    @abstractmethod
    async def get_by_local_id(self, mailbox_id: str, local_id: str) -> list[Message]:
        pass

    @abstractmethod
    async def lookup_by_ods_code_and_workflow_id(self, ods_code: str, workflow_id: str) -> list[Mailbox]:
        pass

    @abstractmethod
    async def lookup_by_workflow_id(self, workflow_id: str) -> list[Mailbox]:
        pass
