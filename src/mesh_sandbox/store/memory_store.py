import asyncio
import importlib
import inspect
import logging
import pkgutil
from abc import ABC, abstractmethod
from collections import defaultdict
from types import ModuleType
from typing import Literal, Optional, cast

from fastapi import BackgroundTasks

from .. import plugins as plugins_ns
from ..common import EnvConfig
from ..models.message import Message, MessageEvent, MessageStatus
from .canned_store import CannedStore


class _SandboxPlugin(ABC):

    triggers: list[Literal["message_accepted", "message_acknowledged"]] = []

    @abstractmethod
    async def on_event(self, event: str, message: Message):
        pass


class MemoryStore(CannedStore):
    """
    in memory store, good for 'in-process' testing or small messages
    """

    supports_reset = True
    load_messages = False

    def __init__(self, config: EnvConfig, logger: logging.Logger, plugins_module: ModuleType = plugins_ns):
        super().__init__(config, logger, filter_expired=True)

        self._plugin_registry = self._find_plugins(plugins_module)
        self._plugin_instances: dict[str, list[_SandboxPlugin]] = {}

    def _find_plugins(self, package: ModuleType) -> dict[str, list[type[_SandboxPlugin]]]:
        plugin_classes = defaultdict(list)
        for _, name, _ in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
            module = importlib.import_module(name)
            for _, class_type in inspect.getmembers(module):

                if not inspect.isclass(class_type) or not class_type.__name__.endswith("Plugin"):
                    continue

                self.logger.info(f"potential plugin: {class_type.__name__} found")
                if not hasattr(class_type, "triggers"):
                    self.logger.warning(f"plugin: {class_type.__name__} has no class attr triggers .. not loading")
                    continue

                if not hasattr(class_type, "on_event"):
                    self.logger.warning(f"plugin: {class_type.__name__} has no class attr on_event .. not loading")
                    continue

                if not inspect.iscoroutinefunction(class_type.on_event):
                    self.logger.warning(f"plugin: {class_type.__name__} on_event os not a coroutine.. not loading")
                    continue

                on_event_args = cast(list[str], inspect.getfullargspec(class_type.on_event)[0])

                if not on_event_args:
                    self.logger.warning(
                        f"plugin: {class_type.__name__} on_event expected args event, message .. not loading"
                    )
                    continue

                if not isinstance(inspect.getattr_static(class_type, "on_event"), staticmethod):
                    on_event_args.pop(0)

                if not len(on_event_args) == 2:
                    self.logger.warning(
                        f"plugin: {class_type.__name__} on_event expected args event, message .. not loading"
                    )
                    continue

                for trigger in class_type.triggers:
                    plugin_classes[trigger].append(class_type)

        return cast(dict[str, list[type[_SandboxPlugin]]], plugin_classes)

    @staticmethod
    async def _construct(plugin_type: type[_SandboxPlugin]) -> _SandboxPlugin:
        created = plugin_type()
        return created

    async def on_event(self, event: str, message: Message):

        instances = self._plugin_instances.get(event, [])
        if not instances:
            registered = self._plugin_registry.get(event, [])
            if not registered:
                return

            instances = await asyncio.gather(*[self._construct(plugin_type) for plugin_type in registered])
            self._plugin_instances[event] = instances

        await asyncio.gather(*[plugin.on_event(event, message) for plugin in instances])

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

    async def send_message(self, message: Message, body: bytes, background_tasks: BackgroundTasks) -> Message:

        async with self.lock:
            parts = cast(list[Optional[bytes]], [None for _ in range(message.total_chunks)])

            self.chunks[message.message_id] = parts

            if message.total_chunks > 0:
                await self.receive_chunk(message, 1, body, background_tasks)

            if message.sender.mailbox_id:
                self.outboxes[message.sender.mailbox_id].insert(0, message)
                if message.metadata.local_id:
                    self.local_ids[message.sender.mailbox_id][message.metadata.local_id].insert(0, message)

            if message.status != MessageStatus.ACCEPTED:
                await self.save_message(message)
            else:
                await self._accept_message_no_lock(message, background_tasks)

        background_tasks.add_task(self.on_event, "post_send_message", message)
        return message

    async def save_chunk(self, message: Message, chunk_number: int, chunk: Optional[bytes]):
        self.chunks[message.message_id][chunk_number - 1] = chunk

    async def receive_chunk(
        self, message: Message, chunk_number: int, chunk: Optional[bytes], background_tasks: BackgroundTasks
    ):
        await self.save_chunk(message, chunk_number, chunk)
        background_tasks.add_task(self.on_event, "chunk_received", message)

    async def _get_file_size(self, message: Message) -> int:
        return sum(len(chunk or b"") for chunk in self.chunks.get(message.message_id, []))

    async def _accept_message_no_lock(self, message: Message, background_tasks: BackgroundTasks) -> Message:

        if message.status != MessageStatus.ACCEPTED:
            message.events.insert(0, MessageEvent(status=MessageStatus.ACCEPTED))
        message.file_size = await self._get_file_size(message)
        self.inboxes[message.recipient.mailbox_id].append(message)
        await self.save_message(message)

        background_tasks.add_task(self.on_event, "message_accepted", message)
        return message

    async def accept_message(self, message: Message, background_tasks: BackgroundTasks) -> Message:
        async with self.lock:
            return await self._accept_message_no_lock(message, background_tasks)

    async def acknowledge_message(self, message: Message, background_tasks: BackgroundTasks) -> Message:
        async with self.lock:
            message.events.insert(0, MessageEvent(status=MessageStatus.ACKNOWLEDGED))
            await self.save_message(message)

        background_tasks.add_task(self.on_event, "message_acknowledged", message)
        return message
