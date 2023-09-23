import logging
import os.path
from typing import Any, ClassVar, Optional


class OnMessageAcceptedPlugin:
    def __init__(self):
        self.logger = logging.getLogger("mesh-sandbox")
        with open(os.path.join(os.path.dirname(__file__), "example_plugin.txt"), encoding="utf-8") as f:
            self.config_message = f.read().strip()

    triggers: ClassVar[list[str]] = ["before_accept_message"]

    async def on_event(self, event: str, kwargs: dict[str, Any], err: Optional[Exception] = None):
        if err:
            print(f"plugin received error {event}\n{kwargs}\n{err}")
            return

        print(f"plugin received event {event}")

        message = kwargs.get("message")
        assert message
        self.logger.info(f"message: {message.message_id} accepted - {self.config_message}")

        if not message.metadata.subject:
            return

        if message.metadata.subject == "change me":
            message.metadata.subject = self.config_message
