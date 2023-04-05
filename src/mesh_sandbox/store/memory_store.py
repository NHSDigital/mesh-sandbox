from collections import defaultdict
from typing import Optional, cast

from ..common import EnvConfig
from ..models.message import Message, MessageEvent, MessageStatus
from .canned_store import CannedStore


class MemoryStore(CannedStore):
    """
    in memory store, good for 'in-process' testing or small messages
    """

    supports_reset = True
    load_messages = False

    def __init__(self, config: EnvConfig):
        super().__init__(config, filter_expired=True)

    async def reset(self):
        async with self.lock:
            super().initialise()

    async def reset_mailbox(self, mailbox_id: str):

        async with self.lock:
            self.inboxes[mailbox_id] = []
            self.outboxes[mailbox_id] = []
            self.local_ids[mailbox_id] = defaultdict(list)
            self.mailboxes[mailbox_id].inbox_count = 0

    async def save_message(self, message: Message):
        self.messages[message.message_id] = message

    async def send_message(self, message: Message, body: Optional[bytes] = None) -> Message:

        async with self.lock:
            parts = cast(list[Optional[bytes]], [None for _ in range(message.total_chunks)])

            self.chunks[message.message_id] = parts

            if message.total_chunks > 0:
                await self.receive_chunk(message, 1, body)

            if message.sender.mailbox_id:
                self.outboxes[message.sender.mailbox_id].insert(0, message)
                if message.metadata.local_id:
                    self.local_ids[message.sender.mailbox_id][message.metadata.local_id].insert(0, message)

            if message.status == MessageStatus.ACCEPTED:
                self.inboxes[message.recipient.mailbox_id].append(message)

            await self.save_message(message)

        return message

    async def receive_chunk(self, message: Message, chunk_number: int, chunk: Optional[bytes]):
        self.chunks[message.message_id][chunk_number - 1] = chunk

    async def _get_file_size(self, message: Message) -> int:
        return sum(len(chunk or b"") for chunk in self.chunks.get(message.message_id, []))

    async def accept_message(self, message: Message) -> Message:
        async with self.lock:
            message.events.insert(0, MessageEvent(status=MessageStatus.ACCEPTED))
            message.file_size = await self._get_file_size(message)
            self.inboxes[message.recipient.mailbox_id].append(message)
            await self.save_message(message)

        return message

    async def acknowledge_message(self, message: Message) -> Message:
        async with self.lock:
            message.events.insert(0, MessageEvent(status=MessageStatus.ACKNOWLEDGED))
            await self.save_message(message)
        return message
