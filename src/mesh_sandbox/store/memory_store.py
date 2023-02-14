from typing import cast

from ..common import EnvConfig
from ..models.message import Message, MessageEvent, MessageStatus
from .canned_store import CannedStore


class MemoryStore(CannedStore):
    """
    in memory store, good for 'in-process' testing or small messages
    """

    def __init__(self, config: EnvConfig):
        super().__init__(config, load_messages=False)

    async def reinitialise(self, clear_disk: bool):
        super().initialise()

    async def send_message(self, message: Message, body: bytes):

        async with self.lock:
            parts: list[bytes] = cast(list[bytes], [None for _ in range(message.total_chunks)])

            self.messages[message.message_id] = message
            self.chunks[message.message_id] = parts

            await self.receive_chunk(message, 1, body)

            if message.sender.mailbox_id:
                self.outboxes[message.sender.mailbox_id].insert(0, message)
                if message.metadata.local_id:
                    self.local_ids[message.sender.mailbox_id][message.metadata.local_id].insert(0, message)

            if message.status != MessageStatus.ACCEPTED:
                return

            self.inboxes[message.recipient.mailbox_id].append(message)

    async def receive_chunk(self, message: Message, chunk_number: int, chunk: bytes):
        self.chunks[message.message_id][chunk_number - 1] = chunk

    async def _get_file_size(self, message: Message) -> int:
        return sum(len(chunk) for chunk in self.chunks.get(message.message_id, []))

    async def accept_message(self, message: Message):
        async with self.lock:
            message.events.insert(0, MessageEvent(status=MessageStatus.ACCEPTED))
            message.file_size = await self._get_file_size(message)
            self.inboxes[message.recipient.mailbox_id].append(message)

    async def acknowledge_message(self, message: Message):
        async with self.lock:
            message.events.insert(0, MessageEvent(status=MessageStatus.ACKNOWLEDGED))
            inbox = self.inboxes[message.recipient.mailbox_id]

            for ix, inbox_message in enumerate(inbox):
                if inbox_message.message_id != message.message_id:
                    continue
                inbox.pop(ix)
                break
