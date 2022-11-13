from datetime import datetime
from typing import Optional, Union

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator  # pylint: disable=no-name-in-module

from ..common import MESH_MEDIA_TYPES, exclude_none_json_encoder
from ..models.message import Message
from . import RichMessageV1


class SendMessageV1(BaseModel):
    messageID: str = Field(description="message identifier of the accepted message")

    class Config:
        title = "send_message"
        schema_extra = {"example": {"messageID": "20220228174323222_ABCDEF"}}


class SendMessageV2(BaseModel):
    message_id: str = Field(description="message identifier of the accepted message")

    class Config:
        title = "send_message"
        schema_extra = {"example": {"message_id": "20220228174323222_ABCDEF"}}


class UploadChunkV1(BaseModel):
    messageID: str = Field(default=None, description="message identifier, as supplied in the request url")
    blockID: str = Field(default=None, description="chunk number, as supplied in the request url")

    class Config:
        title = "upload_chunk"
        schema_extra = {"example": {"messageID": "20220228174323222_ABCDEF", "blockID": 3}}


class OutboxMessageV1(RichMessageV1):

    # pylint: disable=E0213
    class Config:
        validate_assignment = True

    @validator("local_id", "message_type", "status_code", "workflow_id", "recipient_name")
    def prevent_nones(cls, name):
        return name or ""


class RichOutboxView(BaseModel):
    valid_at: Optional[str] = Field(description="iso datetime that the result was created")
    messages: list[OutboxMessageV1] = Field(description="list of found messages")
    links: dict[str, str] = Field(description="map of links, e.g. links.next if more results exist")

    class Config:
        validate_assignment = True
        title = "rich_outbox"
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
                        "recipient_name": "TUVTSCBVSSBUZXN0aW5nIDAx",
                        "sender": "X26HC006",
                        "sender_name": "APIM bebop",
                        "sent_date": "2021-11-22T14:35:52.29Z",
                        "status": "Accepted",
                        "status_code": "",
                        "workflow_id": "API-DOCS-TEST",
                    }
                ],
                "links": {
                    "self": "/messageexchange/mb12345/outbox?start_time=2022-05-20T14:35:52Z",
                    "next": (
                        "/messageexchange/mb12345/outbox?start_time=2022-05-20T14:35:52Z&continue_from="
                        "eyJwayI6ICJNQiNNU0cjTUIjMTIzNEhDMTIzNCMiLCAic2siOiAiTUIjTVNHIzIwMjIw"
                        "MjI4MTc0MzIzMTIzX0FDREVEMSMifQ%3D%3D"
                    ),
                },
            }
        }


def map_to_outbox_message(messages: list[Message]) -> list[OutboxMessageV1]:
    return list(
        map(
            lambda msg: OutboxMessageV1(
                message_id=msg.message_id,
                expiry_timestamp=msg.inbox_expiry_timestamp,
                local_id=msg.metadata.local_id,
                message_type=msg.message_type,
                recipient=msg.recipient.mailbox_id,
                recipient_name=msg.recipient.mailbox_name,
                sender=msg.sender.mailbox_id,
                sender_name=msg.sender.mailbox_name,
                sent_date=msg.created_timestamp,
                status=msg.status,
                workflow_id=msg.workflow_id,
            ),
            messages,
        )
    )


def get_rich_outbox_view(messages: list[Message], links: dict[str, str]) -> JSONResponse:
    return JSONResponse(
        content=exclude_none_json_encoder(
            RichOutboxView(
                valid_at=datetime.utcnow().isoformat(),
                messages=map_to_outbox_message(messages),
                links=links,
            )
        ),
        media_type=MESH_MEDIA_TYPES[2],
    )


def send_message_response(message: Message, model_version: int = 1) -> Union[SendMessageV1, SendMessageV2]:

    if model_version < 2:
        return SendMessageV1(messageID=message.message_id)

    return SendMessageV2(message_id=message.message_id)


def upload_chunk_response(message: Message, chunk_number: int, model_version: int = 1) -> Optional[UploadChunkV1]:

    if model_version < 2:
        return UploadChunkV1(messageID=message.message_id, blockID=chunk_number)

    return None
