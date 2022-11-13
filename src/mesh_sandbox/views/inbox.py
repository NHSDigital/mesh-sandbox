from datetime import datetime
from typing import Optional

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field  # pylint: disable=no-name-in-module

from ..common import MESH_MEDIA_TYPES, exclude_none_json_encoder
from ..models.message import Message, MessageStatus
from . import RichMessageV1


class InboxV1(BaseModel):

    messages: list[str] = Field(description="list of message ids in the inbox, up to 'max_results'")

    class Config:
        title = "inbox_v1"
        schema_extra = {"example": {"messages": ["20220228174323222_ABCDEF", "20220228174323333_ABCDEF"]}}


class InboxV2(BaseModel):

    messages: list[str] = Field(description="list of message ids in the inbox, up to 'max_results'")
    links: Optional[dict[str, str]] = Field(description="map of links, e.g. links.next if more results exist")
    approx_inbox_count: Optional[int] = Field(
        description=(
            "approximate inbox count, this is eventually consistent "
            "and should be used as an indication of inbox size only"
        )
    )

    class Config:
        title = "inbox_v2"
        schema_extra = {
            "example": {
                "messages": ["20220228174323222_ABCDEF", "20220228174323333_ABCDEF"],
                "links": {
                    "self": "/messageexchange/mb12345/inbox?max_results=10",
                    "next": "/messageexchange/mb12345/inbox?max_results=10&continue_from=eyJwayI6ICJNQiNNU0cjTUI"
                    "jMTIzNEhDMTIzNCMiLCAic2siOiAiTUIjTVNHIzIwMjIwMjI4MTc0MzIzMTIzX0FDREVEMSMifQ%3D%3D",
                },
                "approx_inbox_count": 100,
            }
        }


class AcknowledgeV1(BaseModel):

    messageId: str = Field(description="message_id as passed in on the url")

    class Config:
        title = "acknowledge_message"
        schema_extra = {"example": {"messageId": ["20220228174323222_ABCDEF"]}}


class InboxMessageV1(RichMessageV1):
    @classmethod
    def from_message(cls, message: Message):
        events = list(
            message.find_status_events(lambda event: event.status in (MessageStatus.ACCEPTED, MessageStatus.ERROR))
        )
        accepted_event = next((ev for ev in events if ev.status == MessageStatus.ACCEPTED), None)
        error_event = next((ev for ev in events if ev.status == MessageStatus.ERROR), None)

        return cls(
            message_id=message.message_id,
            expiry_timestamp=message.inbox_expiry_timestamp,
            local_id=message.metadata.local_id,
            message_type=message.message_type,
            recipient=message.recipient.mailbox_id,
            recipient_name=message.recipient.mailbox_name,
            sender=message.sender.mailbox_id,
            sender_name=message.sender.mailbox_name,
            status=message.status,
            status_code=error_event.code if error_event else None,
            workflow_id=message.workflow_id,
            sent_date=accepted_event.timestamp if accepted_event else None,
        )


class RichInboxView(BaseModel):
    valid_at: Optional[str] = Field(description="iso datetime that the result was created")
    messages: list[InboxMessageV1] = Field(description="list of found messages")
    links: dict[str, str] = Field(description="map of links, e.g. links.next if more results exist")

    @classmethod
    def from_messages_and_links(cls, messages: list[Message], links: dict[str, str]):
        return cls(
            valid_at=datetime.utcnow().isoformat(),
            messages=[InboxMessageV1.from_message(m) for m in messages],
            links=links,
        )

    class Config:
        title = "rich_inbox"
        schema_extra = {
            "example": {
                "valid_at": "2021-11-22T14:35:52.29Z",
                "messages": [
                    {
                        "message_id": "20200601122152994285_D59900",
                        "expiry_timestamp": "2021-11-22T14:35:52.29Z",
                        "local_id": "api-docs-bob-sends-alice-a-chunked-file",
                        "message_type": "DATA",
                        "recipient": "X26HC005",
                        "recipient_name": "Recip mailbox",
                        "sender": "X26HC006",
                        "sender_name": "APIM bebop",
                        "sentDate": "2021-11-22T14:35:52.29Z",
                        "status": "Accepted",
                        "status_code": None,
                        "workflow_id": "API-DOCS-TEST",
                    }
                ],
                "links": {
                    "self": "/messageexchange/X26HC005/inbox/rich?start_time=2022-05-20T14:35:52Z",
                    "next": (
                        "/messageexchange/X26HC005/inbox/rich?start_time=2022-05-20T14:35:52Z&continue_from="
                        "eyJwayI6ICJNQiNNU0cjTUIjMTIzNEhDMTIzNCMiLCAic2siOiAiTUIjTVNHIzIwMjIw"
                        "MjI4MTc0MzIzMTIzX0FDREVEMSMifQ%3D%3D"
                    ),
                },
            }
        }


def get_rich_inbox_view(messages: list[Message], links: dict[str, str]) -> JSONResponse:
    return JSONResponse(
        content=exclude_none_json_encoder(RichInboxView.from_messages_and_links(messages, links)),
        media_type=MESH_MEDIA_TYPES[2],
    )


class InboxCountV1(BaseModel):
    count: int = Field(description="number of messages in the inbox")
    internalID: str = Field(description="internal identifier")
    allResultsIncluded: bool = Field(description="indicates if the count was based on a partial result")


class InboxCountV2(BaseModel):
    count: int = Field(description="number of messages in the inbox")
