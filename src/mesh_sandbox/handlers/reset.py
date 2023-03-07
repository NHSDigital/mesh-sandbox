from typing import Optional

from fastapi import Depends, HTTPException, status

from ..common import EnvConfig
from ..dependencies import get_env_config, get_store
from ..store.base import Store


class ResetHandler:
    def __init__(self, config: EnvConfig = Depends(get_env_config), store: Store = Depends(get_store)):
        self.config = config
        self.store = store

    async def reset(self, clear_disk: bool, mailbox_id: Optional[str] = None):

        if not mailbox_id:
            await self.store.reset(clear_disk)
            return

        mailbox = await self.store.get_mailbox(mailbox_id, accessed=True)
        if not mailbox:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mailbox does not exist")

        await self.store.reset_mailbox(clear_disk, mailbox.mailbox_id)
