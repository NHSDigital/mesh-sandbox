import asyncio
import importlib
import inspect
import logging
import pkgutil
from collections import defaultdict
from types import ModuleType
from typing import cast

from .. import plugins as plugins_ns
from ..models.message import Message
from ..models.plugin import SandboxPlugin


class PluginManager:
    def __init__(self, package: ModuleType = plugins_ns):

        self.logger = logging.getLogger("mesh-sandbox")
        self.plugins = self.find_plugins(package)

    def find_plugins(self, package: ModuleType) -> dict[str, list[type[SandboxPlugin]]]:
        plugin_classes = defaultdict(list)
        for _, name, _ in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
            module = importlib.import_module(name)
            for _, class_type in inspect.getmembers(module):

                if not inspect.isclass(class_type) or not issubclass(class_type, SandboxPlugin):
                    continue
                self.logger.info(f"found plugin: {class_type.__name__}")
                for trigger in class_type.triggers:
                    plugin_classes[trigger].append(class_type)

        return cast(dict[str, list[type[SandboxPlugin]]], plugin_classes)

    @staticmethod
    async def _construct(plugin_type: type[SandboxPlugin]) -> SandboxPlugin:
        created = plugin_type()
        return created

    async def on_event(self, event: str, message: Message):
        registered = self.plugins.get(event, [])
        if not registered:
            return

        instances = await asyncio.gather(*[self._construct(plugin_type) for plugin_type in registered])

        await asyncio.gather(*[plugin.on_event(event, message) for plugin in instances])
