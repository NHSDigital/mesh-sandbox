from typing import Optional

from fastapi import Depends, HTTPException, status

from ..common import EnvConfig
from ..dependencies import get_env_config, get_store
from ..store.base import Store


class ResetHandler:
    def __init__(self, config: EnvConfig = Depends(get_env_config), store: Store = Depends(get_store)):
        self.config = config
        self.store = store

    async def reset(self, clear_disk: Optional[str] = None):

        if self.config.store_mode == "file":
            return await self.store.reinitialise(clear_disk)

        if clear_disk:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="clear_disk is only supported for file store"
            )

        await self.store.reinitialise()
