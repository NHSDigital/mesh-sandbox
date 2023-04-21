from typing import Optional

from pydantic import BaseModel, Field  # pylint: disable=no-name-in-module

from mesh_sandbox.models.message import MessageStatus


class PutReportRequest(BaseModel):
    mailbox_id: str = Field(description="mailbox id to put the report in")
    code: str = Field(description="error code")
    description: str = Field(description="error description")
    workflow_id: str = Field(description="report workflow id")
    subject: Optional[str] = Field(description="report workflow id", default=None)
    local_id: Optional[str] = Field(description="report message local id", default=None)
    status: str = Field(description="report status (error/undeliverable)", default=MessageStatus.UNDELIVERABLE)
    file_name: Optional[str] = Field(description="file name", default=None)
