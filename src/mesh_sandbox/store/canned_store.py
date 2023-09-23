import json
import logging
import os
from collections import defaultdict
from datetime import datetime
from json import JSONDecodeError
from typing import Callable, Optional, cast
from weakref import WeakValueDictionary

from dateutil.relativedelta import relativedelta

from ..common import EnvConfig
from ..models.mailbox import Mailbox
from ..models.message import Message, MessageStatus, MessageType
from ..models.workflow import Workflow
from .base import Store
from .serialisation import deserialise_model


def _accepted_messages(msg: Message) -> bool:
    return msg.status == MessageStatus.ACCEPTED


class CannedStore(Store):
    """
    pre canned messages or mailboxes not editable
    """

    load_messages = True

    def __init__(self, config: EnvConfig, logger: logging.Logger, filter_expired: bool = False):
        self._config = config
        self._canned_data_dir = os.path.join(os.path.dirname(__file__), "data")
        self._mailboxes_data_dir = self.get_mailboxes_data_dir()
        self._filter_expired = filter_expired
        super().__init__(self._config, logger)

        self.initialise()

    def get_mailboxes_data_dir(self) -> str:
        return os.path.join(self._canned_data_dir, "mailboxes")

    def initialise(self):
        self.mailboxes = self._load_mailboxes()
        self.endpoints = self._load_endpoints()
        self.messages = self._load_messages() if self.load_messages else {}
        self.chunks = self._load_chunks() if self.load_messages else defaultdict(list)
        self.inboxes: dict[str, list[Message]] = {mailbox.mailbox_id: [] for mailbox in self.mailboxes.values()}
        self.outboxes: dict[str, list[Message]] = {mailbox.mailbox_id: [] for mailbox in self.mailboxes.values()}
        self.local_ids: dict[str, dict[str, list[Message]]] = {
            mailbox.mailbox_id: defaultdict(list) for mailbox in self.mailboxes.values()
        }
        self._fill_boxes()
        self.messages = cast(dict[str, Message], WeakValueDictionary(self.messages))

    def _fill_boxes(self):
        for message in self.messages.values():
            if message.sender.mailbox_id and message.sender.mailbox_id in self.mailboxes:
                self.outboxes[message.sender.mailbox_id].append(message)

            if message.recipient.mailbox_id not in self.mailboxes:
                continue

            self.inboxes[message.recipient.mailbox_id].append(message)

        for inbox in self.inboxes.values():
            inbox.sort(key=lambda msg: msg.created_timestamp)

        for mailbox_id, outbox in self.outboxes.items():
            outbox.sort(reverse=True, key=lambda msg: msg.created_timestamp)
            for message in outbox:
                if not message.metadata.local_id:
                    continue
                self.local_ids[mailbox_id][message.metadata.local_id].append(message)

        for mailbox in self.mailboxes.values():
            mailbox.inbox_count = sum(
                1 for message in self.inboxes[mailbox.mailbox_id] if message.status == MessageStatus.ACCEPTED
            )

    def _load_endpoints(self) -> dict[str, list[Mailbox]]:
        canned_workflows = os.path.join(self._canned_data_dir, "workflows.jsonl")
        endpoints: dict[str, list[Mailbox]] = defaultdict(list)

        if not os.path.exists(canned_workflows):
            return endpoints

        with open(canned_workflows, encoding="utf-8") as f:
            workflows = [
                cast(Workflow, deserialise_model(json.loads(line), Workflow)) for line in f.readlines() if line.strip()
            ]

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

    def _load_mailboxes(self) -> dict[str, Mailbox]:
        canned_mailboxes = os.path.join(self._canned_data_dir, "mailboxes.jsonl")

        if not os.path.exists(canned_mailboxes):
            return {}

        with open(canned_mailboxes, encoding="utf-8") as f:
            return {
                mailbox.mailbox_id: mailbox
                for mailbox in (
                    cast(Mailbox, deserialise_model(json.loads(line), Mailbox))
                    for line in f.readlines()
                    if line.strip()
                )
            }

    def _load_messages(self) -> dict[str, Message]:
        messages: dict[str, Message] = {}

        if not os.path.exists(self._mailboxes_data_dir):
            return messages

        for mailbox_path in os.scandir(self._mailboxes_data_dir):
            if not mailbox_path.is_dir():
                continue
            mailbox_id = mailbox_path.name.upper().strip()
            if mailbox_id != mailbox_path.name:
                raise ValueError("mailbox directory names should be upper case")

            if mailbox_id not in self.mailboxes:
                self.mailboxes[mailbox_id] = Mailbox(mailbox_id=mailbox_id, mailbox_name="Unknown", password="password")

            inbox_dir = os.path.join(self._mailboxes_data_dir, mailbox_id, "in")
            if not os.path.exists(inbox_dir):
                continue

            for message_path in os.scandir(inbox_dir):
                if not message_path.is_file() or not message_path.name.endswith(".json"):
                    continue

                try:
                    with open(message_path.path, encoding="utf-8") as f:
                        message = deserialise_model(json.load(f), Message)
                        assert message
                        message_expiry_date = message.created_timestamp + relativedelta(
                            days=self.config.message_expiry_days
                        )
                        if self._filter_expired and message_expiry_date <= datetime.utcnow():
                            continue
                        messages[message.message_id] = message
                except JSONDecodeError as e:
                    print(f"failed to load message json {message_path.path}")
                    print(e)

        return messages

    def _load_chunks(self) -> dict[str, list[Optional[bytes]]]:
        chunks: dict[str, list[Optional[bytes]]] = defaultdict(list)

        for message in self.messages.values():
            if not message.recipient.mailbox_id or message.message_type != MessageType.DATA or message.total_chunks < 1:
                continue

            chunks_dir = os.path.join(self._mailboxes_data_dir, message.recipient.mailbox_id, "in", message.message_id)
            message_chunks: list[Optional[bytes]] = [None for _ in range(message.total_chunks)]
            for chunk_no in range(message.total_chunks):
                chunk_path = os.path.join(chunks_dir, str(chunk_no + 1))
                if not os.path.exists(chunk_path):
                    continue
                with open(chunk_path, "rb") as f:
                    message_chunks[chunk_no] = f.read()
            chunks[message.message_id] = message_chunks

        return chunks

    async def get_mailbox(self, mailbox_id: str, accessed: bool = False) -> Optional[Mailbox]:
        mailbox = self.mailboxes.get(mailbox_id)
        if not mailbox:
            return None

        mailbox.inbox_count = len(await self.get_inbox_messages(mailbox_id, _accepted_messages))
        if accessed:
            mailbox.last_accessed = datetime.utcnow()
        return mailbox

    async def get_message(self, message_id: str) -> Optional[Message]:
        return self.messages.get(message_id)

    async def get_file_size(self, message: Message) -> int:
        return sum(len(chunk or b"") for chunk in self.chunks.get(message.message_id, []))

    async def add_to_outbox(self, message: Message):
        """does nothing on this readonly store..."""

    async def add_to_inbox(self, message: Message):
        """does nothing on this readonly store..."""

    async def save_message(self, message: Message):
        raise NotImplementedError

    async def get_chunk(self, message: Message, chunk_number: int) -> Optional[bytes]:
        parts = self.chunks.get(message.message_id, [])
        if not parts or len(parts) < chunk_number:
            return None
        return parts[chunk_number - 1]

    async def save_chunk(self, message: Message, chunk_number: int, chunk: bytes):
        raise NotImplementedError

    async def reset(self):
        raise NotImplementedError

    async def reset_mailbox(self, mailbox_id: str):
        raise NotImplementedError

    async def get_inbox_messages(
        self, mailbox_id: str, predicate: Optional[Callable[[Message], bool]] = None
    ) -> list[Message]:
        inbox = self.inboxes[mailbox_id]
        if not predicate:
            return inbox

        return [m for m in inbox if predicate(m)]

    async def get_outbox(self, mailbox_id: str) -> list[Message]:
        return self.outboxes[mailbox_id]

    async def get_by_local_id(self, mailbox_id: str, local_id: str) -> list[Message]:
        return self.local_ids.get(mailbox_id, {}).get(local_id, [])

    async def lookup_by_ods_code_and_workflow_id(self, ods_code: str, workflow_id: str) -> list[Mailbox]:
        return self.endpoints.get(f"{ods_code}/{workflow_id}", [])

    async def lookup_by_workflow_id(self, workflow_id: str) -> list[Mailbox]:
        return self.endpoints.get(workflow_id, [])
