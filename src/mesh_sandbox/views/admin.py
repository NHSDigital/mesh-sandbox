from __future__ import annotations

from datetime import datetime
from typing import Final

from pydantic import BaseModel, Field  # pylint: disable=no-name-in-module

from mesh_sandbox.models.mailbox import Mailbox
from mesh_sandbox.models.message import (
    Message,
    MessageDeliveryStatus,
    MessageStatus,
    MessageType,
)

_EMPTY: Final[str] = ""


class CreateReportRequest(BaseModel):
    mailbox_id: str = Field(description="mailbox id to put the report in")
    code: str = Field(description="error code")
    description: str = Field(description="error description")
    workflow_id: str = Field(description="report workflow id")
    subject: str | None = Field(description="report workflow id", default=None)
    local_id: str | None = Field(description="report message local id", default=None)
    status: str = Field(description="report status (error/undeliverable)", default=MessageStatus.UNDELIVERABLE)
    file_name: str | None = Field(description="file name", default=None)
    linked_message_id: str | None = Field(description="linked message id", default=None)


class AddMessageEventRequest(BaseModel):
    status: str = Field(description="new message status")
    code: str | None = Field(description="error code", default=None)
    event: str | None = Field(description="error event (SEND/TRANSFER) etc)", default=None)
    description: str | None = Field(description="error description", default=None)
    linked_message_id: str | None = Field(description="linked message id", default=None)


class MailboxDetails(BaseModel):
    mailbox_id: str = Field(description="mailbox id")
    mailbox_name: str = Field(description="mailbox name")
    billing_entity: str | None = Field(default=None, description="billing entity")
    ods_code: str = Field(default="", description="ODS code")
    org_code: str = Field(default="", description="Organisation code")
    org_name: str = Field(default="", description="Organisation name")
    active: bool = Field(default=True, description="Mailbox active flag")

    @classmethod
    def from_mailbox(cls, mailbox: Mailbox) -> MailboxDetails:
        return cls(
            mailbox_id=mailbox.mailbox_id,
            mailbox_name=mailbox.mailbox_name,
            billing_entity=mailbox.billing_entity,
            ods_code=mailbox.ods_code,
            org_code=mailbox.org_code,
            org_name=mailbox.org_name,
            active=mailbox.active,
        )


class MessageDetails(BaseModel):
    checksum: str | None = Field(description="message status e.g. 'accepted' 'acknowledged'")
    chunk_count: int | None = Field(description="number of message chunks")
    content_encoding: str | None = _EMPTY
    download_timestamp: datetime | None = Field(description="timestamp the message was acknowledged")
    expiry_time: datetime | None = Field(description="timestamp that the message will expire from the inbox")
    failure_date: datetime | None = None
    failure_diagnostic: str | None = None
    filename: str | None = Field(description="local filename as supplied by the sender")
    file_size: int | None = Field(description="the uploaded file size")

    is_compressed: bool | None = False
    is_encrypted: bool | None = False
    linked_msg_id: str | None = Field(description="related message id")
    local_id: str | None = Field(description="local identifier supplied by sender")
    message_id: str = Field(description="message identifier of the sent message")
    message_type: str | None = Field(description="DATA or REPORT")

    recipient: str | None = Field(description="recipient mailbox identifier")
    recipient_name: str | None = Field(description="recipient mailbox name")
    recipient_ods_code: str | None = Field(description="recipient organisation ODS code")
    recipient_org_code: str | None = Field(description="recipient organisation code")
    recipient_org_name: str | None = Field(description="recipient organisation name")

    sender: str | None = Field(description="sender mailbox identifier")
    sender_name: str | None = Field(description="sender mailbox name")
    sender_ods_code: str | None = Field(description="sender ods code")
    sender_org_code: str | None = Field(description="sender organisation code")
    sender_org_name: str | None = Field(description="sender organisation name")

    status: str | None = Field(description="message status e.g. 'accepted' 'acknowledged'")
    status_code: str | None = Field(description="status code")
    status_description: str | None = Field(description="status description")
    status_event: str | None = Field(description="status event")
    status_success: str | None = Field(description="SUCCESS or ERROR if the message accepted")
    status_timestamp: datetime | None = Field(description="timestamp of the status change")

    subject: str | None = Field(description="message subject")
    upload_timestamp: datetime | None = Field(description="timestamp that the message was accepted")
    workflow_id: str | None = Field(description="message workflow identifier")

    @classmethod
    def from_message(cls, message: Message) -> MessageDetails:
        successful = bool(message.message_type == MessageType.DATA and not message.error_event)

        failure_date = None
        failure_description = None
        status_code = None
        status_description = None
        status_event = None
        status_timestamp = None
        status_timestamp_string = None

        if message.error_event:
            if message.message_type == MessageType.DATA:
                failure_date = message.error_event.timestamp
                failure_description = message.error_event.description
            else:
                status_code = message.error_event.code
                status_description = message.error_event.description
                status_event = message.error_event.event
                status_timestamp = message.error_event.timestamp
                status_timestamp_string = status_timestamp

        return cls(
            checksum=message.metadata.checksum or _EMPTY,
            chunk_count=message.total_chunks,
            content_encoding=message.metadata.content_encoding,
            download_timestamp=message.status_timestamp(MessageStatus.ACKNOWLEDGED),
            expiry_time=message.inbox_expiry_timestamp,
            failure_date=failure_date,
            failure_diagnostic=failure_description,
            filename=message.metadata.file_name or f"{message.message_id}.dat",
            file_size=message.file_size,
            is_compressed=message.metadata.compressed,
            is_encrypted=message.metadata.encrypted,
            linked_msg_id=message.error_event.linked_message_id if message.error_event else None,
            local_id=message.metadata.local_id,
            recipient_ods_code=message.recipient.ods_code,
            message_id=message.message_id,
            message_type=(message.message_type or _EMPTY).title(),
            recipient=message.recipient.mailbox_id,
            recipient_name=message.recipient.mailbox_name,
            recipient_org_code=message.recipient.org_code,
            recipient_org_name=message.recipient.org_name,
            sender=message.sender.mailbox_id,
            sender_name=message.sender.mailbox_name,
            sender_ods_code=message.sender.ods_code,
            sender_org_code=message.sender.org_code,
            sender_org_name=message.sender.org_name,
            status=message.status.title(),
            status_code=status_code,
            status_description=status_description,
            status_event=status_event,
            status_success=MessageDeliveryStatus.SUCCESS if successful else MessageDeliveryStatus.ERROR,
            status_timestamp=status_timestamp_string,
            subject=message.metadata.subject,
            upload_timestamp=message.created_timestamp,
            workflow_id=message.workflow_id,
        )
