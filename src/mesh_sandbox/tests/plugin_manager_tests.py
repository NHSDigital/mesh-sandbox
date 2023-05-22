from uuid import uuid4

from .. import tests as tests_module
from ..common.plugin_manager import PluginManager
from ..models.message import Message
from ..models.plugin import SandboxPlugin


class TestPlugin(SandboxPlugin):

    triggers = ["message_accepted"]

    def real_handler(self, event: str, message: Message):
        pass

    async def on_event(self, event: str, message: Message):
        self.real_handler(event, message)


async def test_plugin_provider():

    manager = PluginManager(package=tests_module)

    calls = []

    def test_handler(_: TestPlugin, event: str, message: Message):
        calls.append((event, message))

    TestPlugin.real_handler = test_handler  # type: ignore[method-assign, assignment]

    assert manager.plugins

    message = Message(message_id=uuid4().hex)

    await manager.on_event("message_accepted", message)

    assert len(calls) == 1

    assert calls[0][0] == "message_accepted"
    assert calls[0][1] == message
