from fastapi import Depends

from ..common import EnvConfig
from ..dependencies import get_env_config, get_store
from ..store.base import Store


class ResetHandler:
    def __init__(self, config: EnvConfig = Depends(get_env_config), store: Store = Depends(get_store)):
        self.config = config
        self.store = store

    async def reset(self, clear_disk: bool):
        await self.store.reinitialise(clear_disk)
