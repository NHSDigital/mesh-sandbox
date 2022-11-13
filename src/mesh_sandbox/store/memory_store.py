from typing import Optional

from ..common import EnvConfig
from ..models.message import Message, MessageEvent, MessageStatus
from .canned_store import CannedStore


class MemoryStore(CannedStore):
    def __init__(self, config: EnvConfig):
        super().__init__(config, load_messages=False)

    @staticmethod
    def _load_messages() -> dict[str, Message]:
        return {}

    async def send_message(self, message: Message, body: bytes):

        async with self.lock:
            parts: list[Optional[bytes]] = [None for _ in range(message.total_chunks)]

            self.messages[message.message_id] = message
            self.message_parts[message.message_id] = parts

            await self.receive_chunk(message, 1, body)

            if message.status != MessageStatus.ACCEPTED:
                return

            self.inboxes[message.recipient.mailbox_id].append(message)
            if not message.sender.mailbox_id:
                return

            self.outboxes[message.sender.mailbox_id].insert(0, message)
            if not message.metadata.local_id:
                return

            self.local_ids[message.sender.mailbox_id][message.metadata.local_id].insert(0, message)

    async def receive_chunk(self, message: Message, chunk_number: int, chunk: bytes):
        self.message_parts[message.message_id][chunk_number - 1] = chunk

    async def accept_message(self, message: Message):
        async with self.lock:
            message.events.insert(0, MessageEvent(status=MessageStatus.ACCEPTED))
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
