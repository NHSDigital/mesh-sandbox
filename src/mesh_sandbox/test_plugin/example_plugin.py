import logging
import os.path

from ..models.message import Message
from ..models.plugin import SandboxPlugin


class PluginResources:
    def __init__(self):
        self.logger = logging.getLogger("mesh-sandbox")
        with open(os.path.join(os.path.dirname(__file__), "example_plugin.txt"), encoding="utf-8", mode="r") as f:
            self.config_message = f.read().strip()


_Resources = PluginResources()


class OnMessageAcceptedPlugin(SandboxPlugin):

    triggers = ["message_accepted"]

    def __init__(self):
        self.resources = _Resources

    async def on_event(self, event: str, message: Message):
        self.resources.logger.info(f"message: {message.message_id} accepted - {self.resources.config_message}")
        message.metadata.subject = self.resources.config_message
