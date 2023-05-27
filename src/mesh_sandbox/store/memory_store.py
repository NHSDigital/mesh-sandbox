import logging
from collections import defaultdict
from typing import Optional

from ..common import EnvConfig
from ..models.message import Message
from .canned_store import CannedStore


class MemoryStore(CannedStore):
    """
    in memory store, good for 'in-process' testing or small messages
    """

    readonly = False
    load_messages = False

    def __init__(self, config: EnvConfig, logger: logging.Logger):
        super().__init__(config, logger, filter_expired=True)

    async def reset(self):
        super().initialise()

    async def reset_mailbox(self, mailbox_id: str):
        self.inboxes[mailbox_id] = []
        self.outboxes[mailbox_id] = []
        self.local_ids[mailbox_id] = defaultdict(list)
        self.mailboxes[mailbox_id].inbox_count = 0

    async def add_to_outbox(self, message: Message):
        if not message.sender.mailbox_id:
            return

        self.outboxes[message.sender.mailbox_id].insert(0, message)
        if not message.metadata.local_id:
            return

        self.local_ids[message.sender.mailbox_id][message.metadata.local_id].insert(0, message)

    async def add_to_inbox(self, message: Message):
        self.inboxes[message.recipient.mailbox_id].append(message)

    async def save_message(self, message: Message):
        self.messages[message.message_id] = message

    async def save_chunk(self, message: Message, chunk_number: int, chunk: Optional[bytes]):
        if message.message_id not in self.chunks:
            self.chunks[message.message_id] = [None for _ in range(message.total_chunks)]
        self.chunks[message.message_id][chunk_number - 1] = chunk
