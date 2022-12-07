from datetime import datetime
from typing import Final, Optional, Union

from pydantic import BaseModel, Field  # pylint: disable=no-name-in-module

from ..models.message import Message, MessageDeliveryStatus, MessageStatus, MessageType

_EMPTY: Final[str] = ""


class TrackingV1(BaseModel):

    addressType: Optional[str] = "ALL"
    checksum: Optional[str] = Field(description="message status e.g. 'accepted' 'acknowledged'")
    chunkCount: Optional[int] = Field(description="number of message chunks")
    compressFlag: Optional[str] = None
    contentEncoding: Optional[str] = _EMPTY
    downloadTimestamp: Optional[str] = Field(description="timestamp the message was acknowledged")
    dtsId: str = Field(description="message identifier of the sent message")
    encryptedFlag: Optional[str] = None
    expiryTime: Optional[str] = Field(description="timestamp that the message will expire from the inbox")
    failureDate: Optional[str] = None
    failureDiagnostic: Optional[str] = None
    fileName: Optional[str] = Field(description="local filename as supplied by the sender")
    fileSize: int = Field(description="the uploaded file size")

    isCompressed: Optional[str] = _EMPTY
    linkedMsgId: Optional[str] = Field(description="related message id")
    localId: Optional[str] = Field(description="local identifier supplied by sender")
    meshRecipientOdsCode: Optional[str] = Field(description="recipient organisation ODS code")
    messageId: str = Field(description="message identifier of the sent message")
    messageType: Optional[str] = Field(description="DATA or REPORT")
    partnerId: Optional[str] = _EMPTY

    recipient: Optional[str] = Field(description="recipient mailbox identifier")
    recipientName: Optional[str] = Field(description="recipient mailbox name")
    recipientOrgCode: Optional[str] = Field(description="recipient organisation code")
    recipientOrgName: Optional[str] = Field(description="recipient organisation name")
    recipientSmtp: Optional[str] = _EMPTY

    sender: Optional[str] = Field(description="sender mailbox identifier")
    senderName: Optional[str] = Field(description="sender mailbox name")
    senderOdsCode: Optional[str] = Field(description="sender ods code")
    senderOrgCode: Optional[str] = Field(description="sender organisation code")
    senderOrgName: Optional[str] = Field(description="sender organisation name")
    senderSmtp: Optional[str] = _EMPTY
    status: Optional[str] = Field(description="message status e.g. 'accepted' 'acknowledged'")

    statusCode: Optional[str] = Field(description="status code")
    statusDescription: Optional[str] = Field(description="status description")
    statusEvent: Optional[str] = Field(description="status event")
    statusSuccess: Optional[str] = Field(description="SUCCESS or ERROR if the message accepted")
    statusTimestamp: Optional[str] = Field(description="timestamp of the status change")

    subject: Optional[str] = Field(description="message subject")
    uploadTimestamp: Optional[str] = Field(description="timestamp that the message was accepted")
    version: str = "1.0"
    workflowId: Optional[str] = Field(description="message workflow identifier")

    class Config:
        title = "tracking_v1"


class TrackingV2(BaseModel):

    message_id: str = Field(description="message identifier")
    local_id: Optional[str] = Field(description="local identifier supplied by sender")
    workflow_id: Optional[str] = Field(description="message workflow identifier")
    filename: Optional[str] = Field(description="local filename as supplied by the sender")

    expiry_time: Optional[datetime] = Field(description="iso timestamp that the message will expire from the inbox")
    upload_timestamp: Optional[datetime] = Field(description="iso timestamp that the message was accepted")

    recipient: Optional[str] = Field(description="recipient mailbox identifier")
    recipient_name: Optional[str] = Field(description="recipient mailbox name")
    recipient_ods_code: Optional[str] = Field(description="recipient organisation ODS code")
    recipient_org_code: Optional[str] = Field(description="recipient organisation organisation code")
    recipient_org_name: Optional[str] = Field(description="recipient organisation name")

    status_success: Optional[bool] = Field(description="SUCCESS or ERROR if the message accepted")
    status: Optional[str] = Field(description="message status e.g. 'accepted' 'acknowledged'")
    status_event: Optional[str] = Field(description="status event")
    status_timestamp: Optional[datetime] = Field(description="iso timestamp last status change")
    status_description: Optional[str] = Field(description="status description")
    status_code: Optional[str] = Field(description="status code")

    class Config:
        title = "tracking_v2"


_TIMESTAMP_FORMAT = "%Y%m%d%H%m%S"


def _format_timestamp(timestamp: Optional[datetime]) -> str:
    if not timestamp:
        return ""
    return timestamp.strftime("%Y%m%d%H%M%S")


def create_tracking_response(message: Message, model_version: int = 1) -> Union[TrackingV1, TrackingV2]:

    error_event = message.error_event

    successful = bool(message.message_type == MessageType.DATA and not error_event)

    failure_date = None
    failure_description = None
    status_code = None
    status_description = None
    status_event = None
    status_timestamp = None

    if error_event:
        if message.message_type == MessageType.DATA:
            failure_date = _format_timestamp(error_event.timestamp)
            failure_description = error_event.description
        else:
            status_code = error_event.code
            status_description = error_event.description
            status_event = error_event.event
            status_timestamp = _format_timestamp(error_event.timestamp)

    if model_version < 2:

        return TrackingV1(
            checksum=message.metadata.checksum or _EMPTY,
            chunkCount=message.total_chunks,
            compressFlag="Y" if message.metadata.is_compressed else _EMPTY,
            contentEncoding=message.metadata.content_encoding,
            downloadTimestamp=_format_timestamp(message.status_timestamp(MessageStatus.ACKNOWLEDGED)),
            dtsId=message.message_id,
            encryptedFlag="Y" if message.metadata.encrypted else _EMPTY,
            expiryTime=_format_timestamp(message.inbox_expiry_timestamp),
            failureDate=failure_date,
            failureDiagnostic=failure_description,
            fileName=message.metadata.file_name or f"{message.message_id}.dat",
            fileSize=message.file_size,
            isCompressed="Y" if message.metadata.is_compressed else _EMPTY,
            linkedMsgId=error_event.linked_message_id if error_event else None,
            localId=message.metadata.local_id,
            meshRecipientOdsCode=message.recipient.ods_code,
            messageId=message.message_id,
            messageType=(message.message_type or _EMPTY).title(),
            partnerId=message.metadata.partner_id or _EMPTY,
            recipient=message.recipient.mailbox_id,
            recipientName=message.recipient.mailbox_name,
            recipientOrgCode=message.recipient.org_code,
            recipientOrgName=message.recipient.org_name,
            sender=message.sender.mailbox_id,
            senderName=message.sender.mailbox_name,
            senderOdsCode=message.sender.ods_code,
            senderOrgCode=message.sender.org_code,
            senderOrgName=message.sender.org_name,
            status=message.status.title(),
            statusCode=status_code,
            statusDescription=status_description,
            statusEvent=status_event,
            statusSuccess=MessageDeliveryStatus.SUCCESS if successful else MessageDeliveryStatus.ERROR,
            statusTimestamp=status_timestamp,
            subject=message.metadata.subject,
            uploadTimestamp=_format_timestamp(message.created_timestamp),
            workflowId=message.workflow_id,
        )

    return TrackingV2(
        message_id=message.message_id,
        local_id=message.metadata.local_id,
        workflow_id=message.workflow_id,
        filename=message.metadata.file_name,
        expiry_time=message.inbox_expiry_timestamp,
        upload_timestamp=message.created_timestamp,
        recipient=message.recipient.mailbox_id,
        recipient_name=message.recipient.mailbox_name,
        recipient_ods_code=message.recipient.ods_code,
        recipient_org_code=message.recipient.org_code,
        recipient_org_name=message.recipient.org_name,
        status=message.status,
        status_success=successful,
        status_event=status_event,
        status_timestamp=status_timestamp,
        status_description=status_description,
        status_code=status_code,
    )
