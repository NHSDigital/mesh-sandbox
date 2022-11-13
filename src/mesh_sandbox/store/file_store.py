import os.path
from typing import Optional

from ..common import EnvConfig
from ..models.message import Message, MessageEvent, MessageStatus
from .memory_store import MemoryStore


class FileStore(MemoryStore):
    def __init__(self, config: EnvConfig):
        super().__init__(config)
        self._base_dir = config.file_store_dir

    def chunk_path(self, message: Message, chunk_number: int) -> str:
        return os.path.join(self._base_dir, f"{message.recipient.mailbox_id}/in/{message.message_id}/{chunk_number}")

    async def send_message(self, message: Message, body: bytes):

        async with self.lock:

            self.messages[message.message_id] = message

            with open(self.chunk_path(message, 1), "wb+") as f:
                f.write(body)

            if message.status != MessageStatus.ACCEPTED:
                return
            self.inboxes[message.recipient.mailbox_id].append(message)
            if message.sender.mailbox_id:
                self.outboxes[message.sender.mailbox_id].insert(0, message)
                if message.metadata.local_id:
                    self.local_ids[message.sender.mailbox_id][message.metadata.local_id].insert(0, message)

    async def receive_chunk(self, message: Message, chunk_number: int, chunk: bytes):

        with open(self.chunk_path(message, chunk_number), "wb+") as f:
            f.write(chunk)

    async def retrieve_chunk(self, message: Message, chunk_number: int) -> Optional[bytes]:

        chunk_path = self.chunk_path(message, chunk_number)
        if not os.path.exists(chunk_path):
            return None

        with open(chunk_path, "rb+") as f:
            return f.read()
