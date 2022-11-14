import asyncio
import json
import os
import threading
from collections import defaultdict
from datetime import datetime
from typing import Optional, cast

from ..common import EnvConfig
from ..models.mailbox import Mailbox
from ..models.message import Message
from ..models.workflow import Workflow
from .base import Store
from .serialisation import deserialise_model


class CannedStore(Store):
    """
    pre canned messages or mailboxes not editable
    """

    def __init__(self, config: EnvConfig, load_messages: bool = True):
        super().__init__(config)
        self._sync_lock = threading.Lock()
        self._lock = None
        self.mailboxes = self._load_mailboxes()
        self.endpoints = self._load_endpoints()
        self.messages = self._load_messages() if load_messages else {}
        self.chunks = self._load_chunks() if load_messages else {}
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

    def _load_endpoints(self) -> dict[str, list[Mailbox]]:

        with open(os.path.join(os.path.dirname(__file__), "data/workflows.jsonl"), "r", encoding="utf-8") as f:
            workflows = list(
                cast(Workflow, deserialise_model(json.loads(line), Workflow)) for line in f.readlines() if line.strip()
            )
            endpoints = defaultdict(list)
            for workflow in workflows:

                receivers = workflow.receivers
                for receiver in receivers:
                    receiver = (receiver or "").strip().upper()
                    mailbox = self.mailboxes.get(receiver)
                    if not mailbox:
                        continue

                    endpoints[workflow.workflow_id].append(mailbox)
                    ods_code = (mailbox.ods_code or "").strip().upper()
                    if not ods_code:
                        continue
                    endpoints[f"{ods_code}/{workflow.workflow_id}"].append(mailbox)

            return endpoints

    @staticmethod
    def _load_mailboxes() -> dict[str, Mailbox]:

        with open(os.path.join(os.path.dirname(__file__), "data/mailboxes.jsonl"), "r", encoding="utf-8") as f:
            return {
                mailbox.mailbox_id: mailbox
                for mailbox in (
                    cast(Mailbox, deserialise_model(json.loads(line), Mailbox))
                    for line in f.readlines()
                    if line.strip()
                )
            }

    @staticmethod
    def _load_messages() -> dict[str, Message]:

        with open(os.path.join(os.path.dirname(__file__), "data/messages.jsonl"), "r", encoding="utf-8") as f:
            return {
                message.message_id: message
                for message in (
                    cast(Message, deserialise_model(json.loads(line), Message))
                    for line in f.readlines()
                    if line.strip()
                )
            }

    @staticmethod
    def _load_chunks() -> dict[str, list[Optional[bytes]]]:

        return {}

        # with open(os.path.join(os.path.dirname(__file__), "data/messages.jsonl"), "r", encoding="utf-8") as f:
        #     return {
        #         mailbox.message_id: mailbox
        #         for mailbox in (Message(**json.loads(line)) for line in f.readlines() if line.strip())
        #     }

    async def get_mailbox(self, mailbox_id: str, accessed: bool = False) -> Optional[Mailbox]:
        mailbox = self.mailboxes.get(mailbox_id)
        if not mailbox:
            return None

        mailbox.inbox_count = len(self.inboxes[mailbox_id])
        if accessed:
            mailbox.last_accessed = datetime.utcnow()
        return mailbox

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

    async def get_outbox(self, mailbox_id: str) -> list[Message]:
        return self.outboxes[mailbox_id]

    async def get_by_local_id(self, mailbox_id: str, local_id: str) -> list[Message]:
        return self.local_ids.get(mailbox_id, {}).get(local_id, [])

    async def retrieve_chunk(self, message: Message, chunk_number: int) -> Optional[bytes]:
        parts: list[Optional[bytes]] = self.chunks.get(message.message_id, [])
        if not parts or len(parts) < chunk_number:
            return None
        return parts[chunk_number - 1]

    async def lookup_by_ods_code_and_workflow_id(self, ods_code: str, workflow_id: str) -> list[Mailbox]:
        return self.endpoints.get(f"{ods_code}/{workflow_id}", [])

    async def lookup_by_workflow_id(self, workflow_id: str) -> list[Mailbox]:
        return self.endpoints.get(workflow_id, [])
