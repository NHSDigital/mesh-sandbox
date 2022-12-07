from typing import Optional

from fastapi import Depends, HTTPException
from fastapi import status as http_status
from starlette.responses import JSONResponse

from ..common import MESH_MEDIA_TYPES, EnvConfig, exclude_none_json_encoder
from ..dependencies import get_env_config, get_store
from ..models.mailbox import Mailbox
from ..models.message import Message
from ..store.base import Store
from ..views.tracking import create_tracking_response


class TrackingHandler:
    def __init__(self, config: EnvConfig = Depends(get_env_config), store: Store = Depends(get_store)):
        self.config = config
        self.store = store

    async def tracking_by_message_id(self, sender_mailbox: Mailbox, message_id: str, accepts_api_version: int = 1):

        message: Optional[Message] = await self.store.get_message(message_id)

        if not message:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND)

        if sender_mailbox.mailbox_id != message.sender.mailbox_id or not sender_mailbox.mailbox_id:
            # intentionally not a 403 (matching spine)
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND)

        model = create_tracking_response(message, accepts_api_version)
        return JSONResponse(content=exclude_none_json_encoder(model), media_type=MESH_MEDIA_TYPES[accepts_api_version])

    async def tracking_by_local_id(self, sender_mailbox: Mailbox, local_id: str):

        messages: list[Message] = await self.store.get_by_local_id(sender_mailbox.mailbox_id, local_id)

        if len(messages) == 0:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND)

        if len(messages) > 1:
            raise HTTPException(status_code=http_status.HTTP_300_MULTIPLE_CHOICES)

        message = messages[0]
        model = create_tracking_response(message, 1)
        return JSONResponse(content=exclude_none_json_encoder(model))
