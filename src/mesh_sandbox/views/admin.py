from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field  # pylint: disable=no-name-in-module

from mesh_sandbox.models.mailbox import Mailbox
from mesh_sandbox.models.message import MessageStatus


class CreateReportRequest(BaseModel):
    mailbox_id: str = Field(description="mailbox id to put the report in")
    code: str = Field(description="error code")
    description: str = Field(description="error description")
    workflow_id: str = Field(description="report workflow id")
    subject: Optional[str] = Field(description="report workflow id", default=None)
    local_id: Optional[str] = Field(description="report message local id", default=None)
    status: str = Field(description="report status (error/undeliverable)", default=MessageStatus.UNDELIVERABLE)
    file_name: Optional[str] = Field(description="file name", default=None)
    linked_message_id: Optional[str] = Field(description="linked message id", default=None)


class AddMessageEventRequest(BaseModel):
    status: str = Field(description="new message status")
    code: Optional[str] = Field(description="error code", default=None)
    event: Optional[str] = Field(description="error event (SEND/TRANSFER) etc)", default=None)
    description: Optional[str] = Field(description="error description", default=None)
    linked_message_id: Optional[str] = Field(description="linked message id", default=None)


class MailboxDetails(BaseModel):
    mailbox_id: str = Field(description="mailbox id")
    mailbox_name: str = Field(description="mailbox name")
    billing_entity: Optional[str] = Field(default=None, description="billing entity")
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
