from abc import ABC, abstractmethod
from typing import Literal

from .message import Message


class SandboxPlugin(ABC):

    triggers: list[Literal["message_accepted", "message_acknowledged"]] = []

    @abstractmethod
    async def on_event(self, event: str, message: Message):
        pass
