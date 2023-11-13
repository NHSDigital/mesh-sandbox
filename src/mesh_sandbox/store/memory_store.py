import logging
from collections import defaultdict
from typing import Optional

from ..common import EnvConfig
from ..models.mailbox import Mailbox
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
        all_message_ids = set()
        for message in self.inboxes[mailbox_id]:
            all_message_ids.add(message.message_id)
        for message in self.outboxes[mailbox_id]:
            all_message_ids.add(message.message_id)
        for messages in self.local_ids[mailbox_id].values():
            for message in messages:
                all_message_ids.add(message.message_id)
        for message_id in all_message_ids:
            del self.messages[message_id]
            del self.chunks[message_id]
        self.inboxes[mailbox_id] = []
        self.outboxes[mailbox_id] = []
        self.local_ids[mailbox_id] = defaultdict(list)
        self.mailboxes[mailbox_id].inbox_count = 0

    async def create_mailbox(self, mailbox_id: str):
        self.inboxes[mailbox_id] = []
        self.outboxes[mailbox_id] = []
        self.local_ids[mailbox_id] = defaultdict(list)
        self.mailboxes[mailbox_id] = Mailbox(mailbox_id=mailbox_id, mailbox_name="Unknown", password="password")

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
