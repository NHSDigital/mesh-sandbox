import os.path
import shutil
from typing import Optional

from ..common import EnvConfig
from ..models.message import Message
from .memory_store import MemoryStore


class FileStore(MemoryStore):

    """file based store, will store the message payloads in the filesystem"""

    def __init__(self, config: EnvConfig):
        super().__init__(config)
        self._base_dir = config.file_store_dir

    async def reinitialise(self, clear_disk: bool):
        await super().reinitialise(clear_disk)
        # recursive delete, but preserve top-level folder
        if clear_disk:
            for file in os.listdir(self._base_dir):
                path = os.path.join(self._base_dir, file)
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)

    async def _get_file_size(self, message: Message) -> int:
        size = 0
        message_dir = os.path.join(self._base_dir, f"{message.recipient.mailbox_id}/in/{message.message_id}")
        for file in os.listdir(message_dir):
            stat = os.stat(f"{message_dir}/{file}")
            size += stat.st_size
        return size

    def chunk_path(self, message: Message, chunk_number: int) -> str:
        return os.path.join(self._base_dir, f"{message.recipient.mailbox_id}/in/{message.message_id}/{chunk_number}")

    async def receive_chunk(self, message: Message, chunk_number: int, chunk: bytes):
        chunk_path = self.chunk_path(message, chunk_number)
        os.makedirs(os.path.dirname(chunk_path), exist_ok=True)
        with open(chunk_path, "wb+") as f:
            f.write(chunk)

    async def retrieve_chunk(self, message: Message, chunk_number: int) -> Optional[bytes]:

        chunk_path = self.chunk_path(message, chunk_number)
        if not os.path.exists(chunk_path):
            return None

        with open(chunk_path, "rb+") as f:
            return f.read()
