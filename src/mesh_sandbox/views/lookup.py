from typing import Union
from uuid import uuid4

from pydantic import BaseModel, Field  # pylint: disable=no-name-in-module

from ..models.mailbox import Mailbox


class EndpointLookupItemV1(BaseModel):
    address: str = Field(description="mailbox identifier")
    description: str = Field(description="mailbox name")
    endpoint_type: str = Field(description="mailbox endpoint type, this will always be MESH")

    class Config:
        title = "endpoint_lookup_item_v1"
        json_schema_extra = {
            "example": {"address": "X2612345", "description": "this is a test mailbox", "endpoint_type": "MESH"}
        }


class EndpointLookupV1(BaseModel):
    query_id: str = Field(description="unique query identifier")
    results: list[EndpointLookupItemV1] = Field(description="list of matched mailboxes")

    class Config:
        title = "endpoint_lookup_v1"
        json_schema_extra = {
            "example": {
                "query_id": "20220228174323222_ABCDEF",
                "results": {"address": "X2612345", "description": "this is a test mailbox", "endpoint_type": "MESH"},
            }
        }


class MailboxLookupItem(BaseModel):
    mailbox_id: str = Field(description="mailbox identifier")
    mailbox_name: str = Field(description="mailbox name")

    class Config:
        title = "lookup_item_v2"
        json_schema_extra = {"example": {"mailbox_id": "X2612345", "mailbox_name": "this is a test mailbox"}}


class MailboxLookupV2(BaseModel):
    results: list[MailboxLookupItem] = Field(description="list of matched mailboxes")

    class Config:
        title = "lookup_v2"
        json_schema_extra = {
            "example": {"results": {"mailbox_id": "X2612345", "mailbox_name": "this is a test mailbox"}}
        }


def endpoint_lookup_response(
    mailboxes: list[Mailbox], model_version: int = 1
) -> Union[EndpointLookupV1, MailboxLookupV2]:
    if model_version < 2:
        return EndpointLookupV1(
            query_id=uuid4().hex,
            results=[
                EndpointLookupItemV1(address=mailbox.mailbox_id, description=mailbox.mailbox_name, endpoint_type="MESH")
                for mailbox in mailboxes
            ],
        )

    return MailboxLookupV2(
        results=[
            MailboxLookupItem(
                mailbox_id=mailbox.mailbox_id,
                mailbox_name=mailbox.mailbox_name,
            )
            for mailbox in mailboxes
        ]
    )


# pylint: disable=unused-argument
def workflow_search_response(mailboxes: list[Mailbox], model_version: int = 1) -> MailboxLookupV2:
    return MailboxLookupV2(
        results=[
            MailboxLookupItem(
                mailbox_id=mailbox.mailbox_id,
                mailbox_name=mailbox.mailbox_name,
            )
            for mailbox in mailboxes
        ]
    )
