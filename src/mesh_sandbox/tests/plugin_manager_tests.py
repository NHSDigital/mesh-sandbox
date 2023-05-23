import logging
from uuid import uuid4

from .. import tests as tests_module
from ..common import EnvConfig
from ..models.message import Message
from ..store.memory_store import MemoryStore


class TestPlugin:

    triggers = ["message_accepted"]

    def real_handler(self, event: str, message: Message):
        pass

    async def on_event(self, event: str, message: Message):
        self.real_handler(event, message)


async def test_plugin_provider():

    manager = MemoryStore(config=EnvConfig(), logger=logging.getLogger("mesh-sandbox"), plugins_module=tests_module)

    calls = []

    def test_handler(_: TestPlugin, event: str, message: Message):
        calls.append((event, message))

    TestPlugin.real_handler = test_handler  # type: ignore[method-assign, assignment]

    assert manager._plugin_registry  # pylint: disable=protected-access

    message = Message(message_id=uuid4().hex)

    await manager.on_event("message_accepted", message)

    assert len(calls) == 1

    assert calls[0][0] == "message_accepted"
    assert calls[0][1] == message
