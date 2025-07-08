from typing import Optional
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, HTTPException, status

from mesh_sandbox.common.exceptions import create_ndr_event, create_ndr_metadata

from ..common.messaging import Messaging
from ..dependencies import get_messaging
from ..models.mailbox import Mailbox
from ..models.message import (
    Message,
    MessageEvent,
    MessageMetadata,
    MessageParty,
    MessageStatus,
    MessageType,
)
from ..views.admin import (
    AddMessageEventRequest,
    CreateReportRequest,
    MailboxDetails,
    MessageDetails,
)


class AdminHandler:
    def __init__(self, messaging: Messaging = Depends(get_messaging)):
        self.messaging = messaging

    async def reset(self, mailbox_id: Optional[str] = None):
        if self.messaging.readonly:
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail="reset not supported for current store mode",
            )

        if not mailbox_id:
            await self.messaging.reset()
            return

        mailbox = await self.messaging.get_mailbox(mailbox_id, accessed=False)
        if not mailbox:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="mailbox does not exist")

        await self.messaging.reset_mailbox(mailbox.mailbox_id)

    async def create_report(self, request: CreateReportRequest, background_tasks: BackgroundTasks) -> Message:
        recipient = await self.messaging.get_mailbox(request.mailbox_id, accessed=False)
        if not recipient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="mailbox does not exist")

        assert request.status in (MessageStatus.UNDELIVERABLE, MessageStatus.ERROR)

        if request.status == MessageStatus.UNDELIVERABLE:
            message_event = create_ndr_event(request)
            message_metadata = create_ndr_metadata(request)
        else:
            message_event = MessageEvent(
                status=request.status,
                event="TRANSFER",
                code=request.code,
                description=request.description,
                linked_message_id=request.linked_message_id,
            )
            message_metadata = MessageMetadata(
                subject=request.subject,
                local_id=request.local_id,
                file_name=request.file_name,
            )

        message = Message(
            events=[
                MessageEvent(status=MessageStatus.ACCEPTED),
                message_event,
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
            metadata=message_metadata,
        )

        await self.messaging.send_message(message=message, body=b"", background_tasks=background_tasks)

        return message

    async def add_message_event(
        self, message_id: str, new_event: AddMessageEventRequest, background_tasks: BackgroundTasks
    ):
        message = await self.messaging.get_message(message_id)
        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        event = MessageEvent(
            status=new_event.status,
            code=new_event.code,
            event=new_event.event,
            description=new_event.description,
            linked_message_id=new_event.linked_message_id,
        )

        message = await self.messaging.add_message_event(message, event, background_tasks)

        return message

    async def get_mailbox_details(self, mailbox_id: str) -> MailboxDetails:
        mailbox: Optional[Mailbox] = await self.messaging.get_mailbox(mailbox_id)
        if not mailbox:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        return MailboxDetails.from_mailbox(mailbox)

    async def get_message_details(self, message_id: str) -> MessageDetails:
        message: Optional[Message] = await self.messaging.get_message(message_id)
        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        return MessageDetails.from_message(message)
