from typing import Optional

from pydantic import BaseModel, Field  # pylint: disable=no-name-in-module

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
    code: str = Field(description="error code", default=None)
    event: str = Field(description="error event (SEND/TRANSFER) etc)", default=None)
    description: str = Field(description="error description", default=None)
    linked_message_id: Optional[str] = Field(description="linked message id", default=None)
