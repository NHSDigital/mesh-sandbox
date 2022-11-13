from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field  # pylint: disable=no-name-in-module


class RichMessageV1(BaseModel):
    message_id: str = Field(description="message identifier")
    expiry_timestamp: Optional[datetime] = Field(
        description="iso datetime that the message will expire from the recipient inbox"
    )  # this is the inbox expiry. not the message expiry.
    local_id: Optional[str] = Field(description="local identifier as supplied by the message sender")
    message_type: Optional[str] = Field(description="DATA or REPORT")
    recipient: str = Field(description="recipient mailbox identifier")
    recipient_name: Optional[str] = Field(description="recipient mailbox name")
    sender: Optional[str] = Field(description="sender mailbox identifier")
    sender_name: Optional[str] = Field(description="sender mailbox name")
    sent_date: Optional[datetime] = Field(description="iso datetime that the message was sent")
    status: str = Field(description="message status e.g. 'acknowledged' 'accepted'")
    status_code: Optional[str] = Field(description="message status code")
    workflow_id: Optional[str] = Field(description="message workflow identifier")
