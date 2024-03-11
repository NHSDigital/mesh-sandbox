import asyncio
import importlib
import inspect
import pkgutil
from abc import ABC, abstractmethod
from collections import defaultdict
from functools import wraps
from types import ModuleType
from typing import Any, Callable, ClassVar, Literal, NamedTuple, Optional, TypeVar, cast

from fastapi import HTTPException, status
from starlette.background import BackgroundTasks

from .. import plugins as plugins_ns
from ..models.mailbox import Mailbox
from ..models.message import Message, MessageEvent, MessageStatus, MessageType
from ..store.base import Store
from . import constants, generate_cipher_text


class _SandboxPlugin(ABC):
    triggers: ClassVar[
        list[
            Literal[
                "before_accept_message",
                "after_accept_message",
                "accept_message_error",
                "before_save_message",
                "after_save_message",
                "save_message_error",
                "before_send_message",
                "after_send_message",
                "send_message_error",
                "before_acknowledge_message",
                "after_acknowledge_message",
                "acknowledge_message_error",
                "before_save_chunk",
                "after_save_chunk",
                "save_chunk_error",
            ]
        ]
    ] = []

    @abstractmethod
    async def on_event(self, event: str, event_args: dict[str, Any], exception: Optional[Exception] = None):
        pass


def _accepted_messages(msg: Message) -> bool:
    return msg.status == MessageStatus.ACCEPTED


T_co = TypeVar("T_co", covariant=True)


class AuthoriseHeaderParts(NamedTuple):
    scheme: str
    mailbox_id: str
    nonce: str
    nonce_count: str
    timestamp: str
    cipher_text: str
    parts: int

    def get_reasons_invalid(self) -> list[str]:
        reasons = []
        if self.parts != 5:
            reasons.append(f"invalid num header parts: {self.parts}")

        if not self.nonce_count.isdigit():
            reasons.append("nonce count is not digits")

        if self.scheme not in (MESH_AUTH_SCHEME, ""):
            reasons.append("invalid auth scheme or mailbox_id contains a space")

        if " " in self.mailbox_id:
            reasons.append("mailbox_id contains a space")

        return reasons


_DEFAULT_PARTS_IF_MISSING = ["" for _ in range(5)]
MESH_AUTH_SCHEME = "NHSMESH"


def try_parse_authorisation_token(auth_token: str) -> Optional[AuthoriseHeaderParts]:
    if not auth_token:
        return None

    auth_token = auth_token.strip()

    scheme = MESH_AUTH_SCHEME if auth_token.upper().startswith(MESH_AUTH_SCHEME) else ""

    if scheme:
        auth_token = auth_token[len(MESH_AUTH_SCHEME) + 1 :]

    auth_token_parts = auth_token.split(":")

    num_parts = len(auth_token_parts)
    auth_token_parts = auth_token_parts + _DEFAULT_PARTS_IF_MISSING

    header_parts = AuthoriseHeaderParts(
        scheme=scheme,
        mailbox_id=auth_token_parts[0],
        nonce=auth_token_parts[1],
        nonce_count=auth_token_parts[2],
        timestamp=auth_token_parts[3],
        cipher_text=auth_token_parts[4],
        parts=num_parts,
    )

    return header_parts


class Messaging:
    def __init__(self, store: Store, plugins_module: ModuleType = plugins_ns):
        self.store = store
        self.logger = store.logger
        self.config = store.config
        self._plugin_registry: dict[str, list[type[_SandboxPlugin]]] = defaultdict(list)
        self._plugin_instances: dict[str, list[_SandboxPlugin]] = {}
        self._find_plugins(plugins_module)

    class _TriggersEvent:
        def __init__(self, event_name: str):
            self.event_name = event_name

        def __call__(self, func):
            if not inspect.iscoroutinefunction(func):
                raise ValueError(f"wrapped function is not awaitable: {func}")

            @wraps(func)
            async def _async_inner(*args, **kwargs):
                if len(args) > 1:
                    raise ValueError(f"only call {func} with kwargs")
                messaging = cast(Messaging, args[0])

                kwargs_for_event = kwargs.copy()
                background_tasks = kwargs_for_event.pop("background_tasks", None)

                await messaging.on_event(f"before_{self.event_name}", kwargs_for_event)

                try:
                    result = await func(*args, **kwargs)
                    if background_tasks:
                        background_tasks.add_task(messaging.on_event, f"after_{self.event_name}", kwargs_for_event)
                    return result
                except Exception as err:
                    if background_tasks:
                        background_tasks.add_task(messaging.on_event, f"{self.event_name}_error", kwargs_for_event, err)
                    raise

            return _async_inner

    class _IfNotReadonly:
        def __call__(self, func):
            if not inspect.iscoroutinefunction(func):
                raise ValueError(f"wrapped function is not awaitable: {func}")

            @wraps(func)
            async def _async_inner(*args, **kwargs):
                messaging = cast(Messaging, args[0])
                if messaging.readonly:
                    return

                return await func(*args, **kwargs)

            return _async_inner

    def _find_plugins(self, package: ModuleType):
        for _, name, _ in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
            module = importlib.import_module(name)
            for _, plugin_type in inspect.getmembers(module):
                if not inspect.isclass(plugin_type) or not plugin_type.__name__.endswith("Plugin"):
                    continue

                self.register_plugin(plugin_type)

    def register_plugin(self, plugin_type: type):
        self.logger.info(f"potential plugin: {plugin_type.__name__} found")
        if not hasattr(plugin_type, "triggers"):
            self.logger.warning(f"plugin: {plugin_type.__name__} has no class attr triggers .. not loading")
            return

        if not hasattr(plugin_type, "on_event"):
            self.logger.warning(f"plugin: {plugin_type.__name__} has no class attr on_event .. not loading")
            return

        plugin_type = cast(type[_SandboxPlugin], plugin_type)

        if not inspect.iscoroutinefunction(plugin_type.on_event):
            self.logger.warning(f"plugin: {plugin_type.__name__} on_event is not a coroutine.. not loading")
            return

        on_event_args = cast(list[str], inspect.getfullargspec(plugin_type.on_event)[0])

        msg_args = (
            f"plugin: {plugin_type.__name__} on_event expected args "
            f"(event: str, event_args: dict[str, Any], error: Exception = None) .. not loading"
        )

        if not on_event_args:
            self.logger.warning(msg_args)
            return

        if not isinstance(inspect.getattr_static(plugin_type, "on_event"), staticmethod):
            on_event_args.pop(0)

        if len(on_event_args) not in (2, 3):
            self.logger.warning(msg_args)
            return

        for trigger in plugin_type.triggers:
            self._plugin_registry[trigger].append(plugin_type)

    @staticmethod
    async def _construct(plugin_type: type[_SandboxPlugin]) -> _SandboxPlugin:
        created = plugin_type()
        return created

    async def on_event(self, event: str, event_args: dict[str, Any], exception: Optional[Exception] = None):
        instances = self._plugin_instances.get(event, [])
        if not instances:
            registered = self._plugin_registry.get(event, [])
            if not registered:
                return

            instances = await asyncio.gather(*[self._construct(plugin_type) for plugin_type in registered])
            self._plugin_instances[event] = instances

        if exception:
            await asyncio.gather(*[plugin.on_event(event, event_args, exception) for plugin in instances])
        else:
            await asyncio.gather(*[plugin.on_event(event, event_args) for plugin in instances])

    @property
    def readonly(self) -> bool:
        return self.store.readonly

    @_TriggersEvent(event_name="send_message")
    async def send_message(self, message: Message, body: bytes, background_tasks: BackgroundTasks) -> Message:
        if message.total_chunks > 0:
            await self.save_chunk(message=message, chunk_number=1, chunk=body, background_tasks=background_tasks)

        if message.total_chunks == 1 or message.message_type == MessageType.REPORT:
            await self.accept_message(message=message, file_size=len(body), background_tasks=background_tasks)
        else:
            await self.save_message(message=message, background_tasks=background_tasks)

        await self.store.add_to_outbox(message)

        return message

    @_TriggersEvent(event_name="accept_message")
    @_IfNotReadonly()
    async def accept_message(self, message: Message, file_size: int, background_tasks: BackgroundTasks):
        if message.status != MessageStatus.ACCEPTED:
            message.events.insert(0, MessageEvent(status=MessageStatus.ACCEPTED))

        message.file_size = file_size

        await self.save_message(message=message, background_tasks=background_tasks)
        await self.store.add_to_inbox(message)

    @_TriggersEvent(event_name="acknowledge_message")
    @_IfNotReadonly()
    async def acknowledge_message(self, message: Message, background_tasks: BackgroundTasks) -> Message:
        if message.status != MessageStatus.ACCEPTED:
            return message

        message.events.insert(0, MessageEvent(status=MessageStatus.ACKNOWLEDGED))
        await self.save_message(message=message, background_tasks=background_tasks)

        return message

    async def add_message_event(
        self, message: Message, event: MessageEvent, background_tasks: BackgroundTasks
    ) -> Message:
        message.events.insert(0, event)
        await self.save_message(message=message, background_tasks=background_tasks)

        return message

    @_TriggersEvent(event_name="save_chunk")
    @_IfNotReadonly()
    async def save_chunk(
        self, message: Message, chunk_number: int, chunk: bytes, background_tasks: BackgroundTasks
    ):  # pylint: disable=unused-argument
        return await self.store.save_chunk(message=message, chunk_number=chunk_number, chunk=chunk)

    @_TriggersEvent(event_name="save_message")
    @_IfNotReadonly()
    async def save_message(
        self, message: Message, background_tasks: Optional[BackgroundTasks] = None
    ):  # pylint: disable=unused-argument
        return await self.store.save_message(message)

    @_IfNotReadonly()
    async def reset(self):
        await self.store.reset()

    @_IfNotReadonly()
    async def reset_mailbox(self, mailbox_id: str):
        await self.store.reset_mailbox(mailbox_id=mailbox_id)

    async def get_chunk(self, message: Message, chunk_number: int) -> Optional[bytes]:
        return await self.store.get_chunk(message=message, chunk_number=chunk_number)

    async def get_mailbox(self, mailbox_id: str, accessed: bool = False) -> Optional[Mailbox]:
        return await self.store.get_mailbox(mailbox_id=mailbox_id, accessed=accessed)

    async def get_message(self, message_id: str) -> Optional[Message]:
        return await self.store.get_message(message_id=message_id)

    async def get_inbox_messages(
        self, mailbox_id: str, predicate: Optional[Callable[[Message], bool]] = None
    ) -> list[Message]:
        return await self.store.get_inbox_messages(mailbox_id=mailbox_id, predicate=predicate)

    async def get_outbox(self, mailbox_id: str) -> list[Message]:
        return await self.store.get_outbox(mailbox_id=mailbox_id)

    async def get_by_local_id(self, mailbox_id: str, local_id: str) -> list[Message]:
        return await self.store.get_by_local_id(mailbox_id=mailbox_id, local_id=local_id)

    async def lookup_by_ods_code_and_workflow_id(self, ods_code: str, workflow_id: str) -> list[Mailbox]:
        return await self.store.lookup_by_ods_code_and_workflow_id(ods_code=ods_code, workflow_id=workflow_id)

    async def lookup_by_workflow_id(self, workflow_id: str) -> list[Mailbox]:
        return await self.store.lookup_by_workflow_id(workflow_id=workflow_id)

    async def get_accepted_inbox_messages(self, mailbox_id: str) -> list[Message]:
        return await self.get_inbox_messages(mailbox_id, _accepted_messages)

    async def _validate_auth_token(self, mailbox_id: str, authorization: str) -> Optional[Mailbox]:
        if self.config.auth_mode == "none":
            return await self.get_mailbox(mailbox_id, accessed=True)

        authorization = (authorization or "").strip()
        if not authorization:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=constants.ERROR_READING_AUTH_HEADER)

        header_parts = try_parse_authorisation_token(authorization)
        if not header_parts:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=constants.ERROR_READING_AUTH_HEADER)

        if header_parts.mailbox_id != mailbox_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=constants.ERROR_MAILBOX_TOKEN_MISMATCH)

        if self.config.auth_mode == "canned":
            if header_parts.nonce.upper() != "VALID":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=constants.ERROR_INVALID_AUTH_TOKEN)
            return await self.get_mailbox(mailbox_id, accessed=True)

        if header_parts.get_reasons_invalid():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=constants.ERROR_READING_AUTH_HEADER)

        mailbox = await self.get_mailbox(mailbox_id, accessed=True)

        if not mailbox:
            return None

        cipher_text = generate_cipher_text(
            self.config.shared_key,
            header_parts.mailbox_id,
            mailbox.password,
            header_parts.timestamp,
            header_parts.nonce,
            header_parts.nonce_count,
        )

        if header_parts.cipher_text.lower() != cipher_text.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=constants.ERROR_INVALID_AUTH_TOKEN)

        return mailbox

    async def authorise_mailbox(self, mailbox_id: str, authorization: str) -> Optional[Mailbox]:
        mailbox = await self._validate_auth_token(mailbox_id, authorization)

        if not mailbox:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=constants.ERROR_NO_MAILBOX_MATCHES)

        return mailbox

    async def get_file_size(self, message: Message) -> int:
        return await self.store.get_file_size(message)
