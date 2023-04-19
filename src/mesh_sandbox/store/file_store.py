import json
import os.path
from collections import defaultdict
from typing import Optional

from ..models.message import Message
from .memory_store import MemoryStore
from .serialisation import serialise_model


class FileStore(MemoryStore):

    """file based store, will store the message payloads in the filesystem"""

    load_messages = True

    def get_mailboxes_data_dir(self) -> str:
        return self._config.mailboxes_dir

    async def _get_file_size(self, message: Message) -> int:
        size = 0
        if message.total_chunks < 1:
            return 0

        message_dir = self.message_path(message)
        for chunk_no in range(message.total_chunks):
            stat = os.stat(f"{message_dir}/{chunk_no+1}")
            size += stat.st_size
        return size

    async def save_message(self, message: Message):
        message_json_path = f"{self.message_path(message)}.json"
        os.makedirs(os.path.dirname(message_json_path), exist_ok=True)
        with open(message_json_path, "w+", encoding="utf-8") as f:
            json.dump(serialise_model(message), f)
        await super().save_message(message)

    def inbox_path(self, mailbox_id: str) -> str:
        return os.path.join(self._mailboxes_data_dir, mailbox_id, "in")

    def message_path(self, message: Message) -> str:
        return os.path.join(self.inbox_path(message.recipient.mailbox_id), message.message_id)

    def chunk_path(self, message: Message, chunk_number: int) -> str:
        return os.path.join(self.message_path(message), str(chunk_number))

    def _load_chunks(self) -> dict[str, list[Optional[bytes]]]:
        return defaultdict(list)

    async def receive_chunk(self, message: Message, chunk_number: int, chunk: Optional[bytes]):
        chunk_path = self.chunk_path(message, chunk_number)
        if chunk is None:
            if not os.path.exists(chunk_path):
                return
            os.remove(chunk_path)
            return

        os.makedirs(os.path.dirname(chunk_path), exist_ok=True)
        with open(chunk_path, "wb+") as f:
            f.write(chunk)

    async def retrieve_chunk(self, message: Message, chunk_number: int) -> Optional[bytes]:

        chunk_path = self.chunk_path(message, chunk_number)
        if not os.path.exists(chunk_path):
            return None

        with open(chunk_path, "rb") as f:
            return f.read()
