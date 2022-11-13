import asyncio
import json
import os
import threading
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from typing import Optional

from ..common import EnvConfig
from ..models.mailbox import AuthorisedMailbox, Mailbox
from ..models.message import Message
from .base import Store


class CannedStore(Store):
    def __init__(self, config: EnvConfig, load_messages: bool = True):
        super().__init__(config)
        self._sync_lock = threading.Lock()
        self._lock = None
        self.mailboxes = self._load_mailboxes()
        self.messages = self._load_messages() if load_messages else {}
        self.message_parts = self._load_parts() if load_messages else {}
        self.inboxes: dict[str, list[Message]] = {mailbox.mailbox_id: [] for mailbox in self.mailboxes.values()}
        self.outboxes: dict[str, list[Message]] = {mailbox.mailbox_id: [] for mailbox in self.mailboxes.values()}
        self.local_ids: dict[str, dict[str, list[Message]]] = {
            mailbox.mailbox_id: defaultdict(list) for mailbox in self.mailboxes.values()
        }
        self._fill_boxes()

    @property
    def lock(self):

        if self._lock is not None:
            return self._lock

        with self._sync_lock:
            if self._lock is not None:
                return self._lock
            self._lock = asyncio.Lock()
            return self._lock

    def _fill_boxes(self):
        for message in self.messages.values():
            if message.sender.mailbox_id and message.sender.mailbox_id in self.mailboxes:
                self.outboxes[message.sender.mailbox_id].append(message)

            if message.recipient.mailbox_id and message.recipient.mailbox_id in self.mailboxes:
                self.inboxes[message.recipient.mailbox_id].append(message)

        for inbox in self.inboxes.values():
            inbox.sort(key=lambda msg: msg.created_timestamp)

        for mailbox_id, outbox in self.outboxes.items():
            outbox.sort(reverse=True, key=lambda msg: msg.created_timestamp)
            for message in outbox:
                if not message.metadata.local_id:
                    continue
                self.local_ids[mailbox_id][message.metadata.local_id].append(message)

    @staticmethod
    def _load_mailboxes() -> dict[str, Mailbox]:

        with open(os.path.join(os.path.dirname(__file__), "data/mailboxes.jsonl"), "r", encoding="utf-8") as f:
            return {
                mailbox.mailbox_id: mailbox
                for mailbox in (Mailbox(**json.loads(line)) for line in f.readlines() if line.strip())
            }

    @staticmethod
    def _load_messages() -> dict[str, Message]:

        with open(os.path.join(os.path.dirname(__file__), "data/messages.jsonl"), "r", encoding="utf-8") as f:
            return {
                mailbox.message_id: mailbox
                for mailbox in (Message(**json.loads(line)) for line in f.readlines() if line.strip())
            }

    @staticmethod
    def _load_parts() -> dict[str, Message]:

        with open(os.path.join(os.path.dirname(__file__), "data/messages.jsonl"), "r", encoding="utf-8") as f:
            return {
                mailbox.message_id: mailbox
                for mailbox in (Message(**json.loads(line)) for line in f.readlines() if line.strip())
            }

    async def get_authorised_mailbox(self, mailbox_id: str) -> Optional[AuthorisedMailbox]:
        mailbox = await self.get_mailbox(mailbox_id)
        if not mailbox:
            return None
        authorised_mailbox = AuthorisedMailbox(**asdict(mailbox))
        authorised_mailbox.inbox_count = len(self.inboxes[mailbox_id])
        authorised_mailbox.last_accessed = datetime.utcnow()
        return authorised_mailbox

    async def get_mailbox(self, mailbox_id: str) -> Optional[Mailbox]:
        return self.mailboxes.get(mailbox_id)

    async def send_message(self, message: Message, body: bytes):
        pass

    async def accept_message(self, message: Message):
        pass

    async def acknowledge_message(self, message: Message):
        pass

    async def receive_chunk(self, message: Message, chunk_number: int, chunk: bytes):
        pass

    async def get_message(self, message_id: str) -> Optional[Message]:
        return self.messages.get(message_id)

    async def get_inbox(self, mailbox_id: str) -> list[Message]:
        return self.inboxes[mailbox_id]

    async def get_by_local_id(self, mailbox_id: str, local_id: str) -> list[Message]:
        return self.local_ids.get(mailbox_id, {}).get(local_id, [])

    async def retrieve_chunk(self, message: Message, chunk_number: int) -> Optional[bytes]:
        parts = self.message_parts.get(message.message_id, [])
        if not parts or len(parts) < chunk_number:
            return None
        return parts[chunk_number - 1]
