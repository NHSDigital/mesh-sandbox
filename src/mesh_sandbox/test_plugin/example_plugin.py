import logging
import os.path


class OnMessageAcceptedPlugin:
    def __init__(self):
        self.logger = logging.getLogger("mesh-sandbox")
        with open(os.path.join(os.path.dirname(__file__), "example_plugin.txt"), encoding="utf-8", mode="r") as f:
            self.config_message = f.read().strip()

    triggers = ["message_accepted"]

    async def on_event(self, event: str, message):  # pylint: disable=unused-argument
        self.logger.info(f"message: {message.message_id} accepted - {self.config_message}")

        if not message.metadata.subject:
            return

        if message.metadata.subject == "change me":
            message.metadata.subject = self.config_message
