from datetime import datetime
from typing import Final, Optional, Union

from pydantic import BaseModel, Field  # pylint: disable=no-name-in-module

from ..models.message import Message, MessageDeliveryStatus, MessageStatus


class TrackingV1(BaseModel):

    messageId: str = Field(description="message identifier of the sent message")
    localId: Optional[str] = Field(description="local identifier supplied by sender")
    statusSuccess: Optional[str] = Field(description="SUCCESS or ERROR if the message accepted")
    messageType: Optional[str] = Field(description="DATA or REPORT")
    statusTimestamp: Optional[datetime] = Field(description="timestamp of the status change")
    recipientName: Optional[str] = Field(description="recipient mailbox name")
    statusCode: Optional[str] = Field(description="status code")
    statusEvent: Optional[str] = Field(description="status event")
    statusDescription: Optional[str] = Field(description="status description")
    status: Optional[str] = Field(description="message status e.g. 'accepted' 'acknowledged'")
    workflowId: Optional[str] = Field(description="message workflow identifier")
    recipientOrgName: Optional[str] = Field(description="recipient organisation name")
    expiryTime: Optional[datetime] = Field(description="timestamp that the message will expire from the inbox")
    fileName: Optional[str] = Field(description="local filename as supplied by the sender")
    meshRecipientOdsCode: Optional[str] = Field(description="recipient organisation ODS code")
    uploadTimestamp: Optional[datetime] = Field(description="timestamp that the message was accepted")
    recipient: Optional[str] = Field(description="recipient mailbox identifier")
    sender: Optional[str] = Field(description="sender mailbox identifier")
    recipientOrgCode: Optional[str] = Field(description="recipient organisation code")

    _DEPRECATED_RESPONSE: Final[str] = "Deprecated"

    # fields in the published response schema which we'll return "deprecated" for
    processId: Optional[str] = _DEPRECATED_RESPONSE
    addressType: Optional[str] = _DEPRECATED_RESPONSE
    recipientBillingEntity: Optional[str] = _DEPRECATED_RESPONSE
    dtsId: Optional[str] = _DEPRECATED_RESPONSE
    senderBillingEntity: Optional[str] = _DEPRECATED_RESPONSE
    senderOdsCode: Optional[str] = _DEPRECATED_RESPONSE
    partnerId: Optional[str] = _DEPRECATED_RESPONSE
    senderName: Optional[str] = _DEPRECATED_RESPONSE
    subject: Optional[str] = _DEPRECATED_RESPONSE
    version: Optional[str] = _DEPRECATED_RESPONSE
    encryptedFlag: Optional[str] = _DEPRECATED_RESPONSE
    senderOrgName: Optional[str] = _DEPRECATED_RESPONSE
    senderOrgCode: Optional[str] = _DEPRECATED_RESPONSE
    senderSmtp: Optional[str] = _DEPRECATED_RESPONSE
    recipientSmtp: Optional[str] = _DEPRECATED_RESPONSE
    compressFlag: Optional[str] = _DEPRECATED_RESPONSE
    checksum: Optional[str] = _DEPRECATED_RESPONSE
    isCompressed: Optional[str] = _DEPRECATED_RESPONSE
    contentEncoding: Optional[str] = _DEPRECATED_RESPONSE
    fileSize: Optional[str] = _DEPRECATED_RESPONSE

    # fields not in the published response schema that we currently send
    inboundFileName: Optional[str] = _DEPRECATED_RESPONSE
    chunkCount: Optional[str] = _DEPRECATED_RESPONSE
    downloadTimestamp: Optional[str] = _DEPRECATED_RESPONSE
    failureDate: Optional[str] = _DEPRECATED_RESPONSE
    failureDiagnostic: Optional[str] = _DEPRECATED_RESPONSE
    linkedMsgId: Optional[str] = _DEPRECATED_RESPONSE
    messageInOverflowState: Optional[str] = _DEPRECATED_RESPONSE
    contentsBase64: Optional[str] = _DEPRECATED_RESPONSE
    expiryPeriod: Optional[str] = _DEPRECATED_RESPONSE

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


def create_tracking_response(message: Message, model_version: int = 1) -> Union[TrackingV1, TrackingV2]:

    successful = message.status in (MessageStatus.ACCEPTED, MessageStatus.ACKNOWLEDGED)

    status_event = message.last_event
    if model_version < 2:

        return TrackingV1(
            messageId=message.message_id,
            localId=message.metadata.local_id,
            statusSuccess=MessageDeliveryStatus.SUCCESS if successful else MessageDeliveryStatus.ERROR,
            messageType=message.message_type,
            statusTimestamp=status_event.timestamp,
            recipientName=message.recipient.mailbox_name,
            statusEvent=status_event.event,
            statusDescription=status_event.description,
            status=message.status,
            workflowId=message.workflow_id,
            recipientOrgName=message.recipient.org_name,
            expiryTime=message.inbox_expiry_timestamp,
            fileName=message.metadata.file_name,
            meshRecipientOdsCode=message.recipient.ods_code,
            uploadTimestamp=message.created_timestamp,
            recipient=message.recipient.mailbox_id,
            sender=message.sender.mailbox_id,
            recipientOrgCode=message.recipient.org_code,
            statusCode=status_event.code,
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
        status_success=successful,
        status=message.status,
        status_event=status_event.event,
        status_timestamp=status_event.timestamp,
        status_description=status_event.description,
        status_code=status_event.code,
    )
