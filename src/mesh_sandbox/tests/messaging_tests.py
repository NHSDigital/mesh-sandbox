from typing import Any, ClassVar, Optional
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks

from .. import tests as tests_module
from ..common.messaging import Messaging
from ..dependencies import get_messaging, get_store
from ..models.message import (
    Message,
    MessageEvent,
    MessageMetadata,
    MessageParty,
    MessageStatus,
)
from .helpers import temp_env_vars


@pytest.fixture(name="message")
def create_message() -> Message:
    message = Message(
        message_id=uuid4().hex.upper(),
        workflow_id=uuid4().hex.upper(),
        sender=MessageParty(mailbox_id=uuid4().hex.upper()),
        recipient=MessageParty(mailbox_id=uuid4().hex.upper()),
        metadata=MessageMetadata(),
        events=[MessageEvent(status=MessageStatus.ACCEPTED)],
    )
    return message


@pytest.fixture(name="background_tasks")
def background_tasks() -> BackgroundTasks:
    return BackgroundTasks()


async def test_canned_store_raises_for_save_message(message: Message):
    with temp_env_vars(STORE_MODE="canned"):
        store = get_store()

        with pytest.raises(NotImplementedError):
            await store.save_message(message)


async def test_canned_messaging_does_not_raise_no_bgt(message: Message):
    calls = []

    class TestPlugin:
        triggers: ClassVar[list[str]] = ["before_save_message", "after_save_message", "save_message_error"]

        async def on_event(self, event: str, args: dict[str, Any], exception: Optional[Exception] = None):
            calls.append((event, args, exception))

    with temp_env_vars(STORE_MODE="canned"):
        messaging = get_messaging()
        messaging.register_plugin(TestPlugin)
        await messaging.save_message(message=message)

    assert len(calls) == 1
    assert calls[0][0] == "before_save_message"


async def test_canned_messaging_does_not_raise_with_bgt(message: Message, background_tasks: BackgroundTasks):
    calls = []

    class Test2Plugin:
        triggers: ClassVar[list[str]] = ["before_save_message", "after_save_message", "save_message_error"]

        async def on_event(self, event: str, args: dict[str, Any], exception: Optional[Exception] = None):
            calls.append((event, args, exception))

    with temp_env_vars(STORE_MODE="canned"):
        messaging = get_messaging()
        messaging.register_plugin(Test2Plugin)
        await messaging.save_message(message=message, background_tasks=background_tasks)

    await background_tasks()

    assert len(calls) == 2
    assert calls[0][0] == "before_save_message"
    assert calls[1][0] == "after_save_message"


async def test_messaging_does_not_raise_with_bgt(message: Message, background_tasks: BackgroundTasks):
    calls = []

    class Test2Plugin:
        triggers: ClassVar[list[str]] = ["before_save_message", "after_save_message", "save_message_error"]

        async def on_event(self, event: str, args: dict[str, Any], exception: Optional[Exception] = None):
            calls.append((event, args, exception))

    with temp_env_vars(STORE_MODE="memory"):
        messaging = get_messaging()
        messaging.register_plugin(Test2Plugin)
        await messaging.save_message(message=message, background_tasks=background_tasks)

    await background_tasks()

    assert len(calls) == 2
    assert calls[0][0] == "before_save_message"
    assert calls[1][0] == "after_save_message"


async def test_error_events_raised_with_bgt(message: Message, background_tasks: BackgroundTasks):
    calls = []

    class Test2Plugin:
        triggers: ClassVar[list[str]] = ["before_save_message", "after_save_message", "save_message_error"]

        async def on_event(self, event: str, args: dict[str, Any], exception: Optional[Exception] = None):
            calls.append((event, args, exception))

    with temp_env_vars(STORE_MODE="memory"):
        messaging = get_messaging()
        messaging.register_plugin(Test2Plugin)
        await messaging.save_message(message=message, background_tasks=background_tasks)

    await background_tasks()

    assert len(calls) == 2
    assert calls[0][0] == "before_save_message"
    assert calls[1][0] == "after_save_message"


class TestDiscoveredPlugin:
    triggers: ClassVar[list[str]] = ["before_accept_message"]

    async def on_event(self, event: str, args: dict[str, Any], err: Optional[Exception] = None):
        pass


async def test_plugin_discovery(monkeypatch):
    messaging = Messaging(store=get_store(), plugins_module=tests_module)

    calls = []

    async def on_event(_, event: str, args: dict[str, Any], err: Optional[Exception] = None):
        calls.append((event, args, err))

    monkeypatch.setattr(TestDiscoveredPlugin, "on_event", on_event)

    assert messaging._plugin_registry  # pylint: disable=protected-access

    message = Message(message_id=uuid4().hex)
    args = {"message": message}

    await messaging.on_event("before_accept_message", args)

    assert len(calls) == 1

    assert calls[0][0] == "before_accept_message"
    assert calls[0][1] == args
    assert calls[0][2] is None
