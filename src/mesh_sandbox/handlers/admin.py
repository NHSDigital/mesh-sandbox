from typing import Optional
from uuid import uuid4

from fastapi import Depends, HTTPException, status

from ..common import EnvConfig
from ..dependencies import get_env_config, get_store
from ..models.message import (
    Message,
    MessageEvent,
    MessageMetadata,
    MessageParty,
    MessageStatus,
    MessageType,
)
from ..store.base import Store
from ..views.admin import PutReportRequest


class AdminHandler:
    def __init__(self, config: EnvConfig = Depends(get_env_config), store: Store = Depends(get_store)):
        self.config = config
        self.store = store

    async def reset(self, mailbox_id: Optional[str] = None):

        if not self.store.supports_reset:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail=f"reset not supported for {self.config.store_mode} store mode",
            )

        if not mailbox_id:
            await self.store.reset()
            return

        mailbox = await self.store.get_mailbox(mailbox_id, accessed=False)
        if not mailbox:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="mailbox does not exist")

        await self.store.reset_mailbox(mailbox.mailbox_id)

    async def put_report(self, request: PutReportRequest) -> Message:
        recipient = await self.store.get_mailbox(request.mailbox_id, accessed=False)
        if not recipient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="mailbox does not exist")

        assert request.status in (MessageStatus.UNDELIVERABLE, MessageStatus.ERROR)

        message = Message(
            events=[
                MessageEvent(status=MessageStatus.ACCEPTED),
                MessageEvent(
                    status=request.status, event="TRANSFER", code=request.code, description=request.description
                ),
            ],
            message_id=uuid4().hex.upper(),
            sender=MessageParty(
                mailbox_id="",
                mailbox_name="Central System Mailbox",
                ods_code="X26",
                org_code="X26",
                org_name="NHS England",
                billing_entity="England",
            ),
            recipient=MessageParty(
                mailbox_id=recipient.mailbox_id,
                mailbox_name=recipient.mailbox_name,
                ods_code=recipient.ods_code,
                org_code=recipient.org_code,
                org_name=recipient.org_name,
                billing_entity=recipient.billing_entity,
            ),
            total_chunks=0,
            message_type=MessageType.REPORT,
            workflow_id=request.workflow_id,
            metadata=MessageMetadata(
                subject=request.subject,
                local_id=request.local_id,
                file_name=request.file_name,
            ),
        )

        await self.store.send_message(message)

        return message
