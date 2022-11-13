from datetime import datetime
from typing import Optional, cast
from uuid import uuid4

from dateutil.relativedelta import relativedelta
from fastapi import Depends, HTTPException, Request
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from ..common import EnvConfig, strtobool
from ..common.constants import Headers
from ..common.handler_helpers import get_handler_uri
from ..common.mex_headers import MexHeaders
from ..dependencies import get_env_config, get_store
from ..models.mailbox import AuthorisedMailbox
from ..models.message import (
    Message,
    MessageEvent,
    MessageMetadata,
    MessageParty,
    MessageStatus,
    MessageType,
)
from ..store.base import Store
from ..views.outbox import (
    get_rich_outbox_view,
    send_message_response,
    upload_chunk_response,
)


def get_chunk_range(chunk_range: str, request_chunk_no: int) -> tuple[Optional[str], int, int]:
    if not chunk_range:
        if request_chunk_no != 1:
            return "header does not match url", 0, 0
        return None, 1, 1

    parts = chunk_range.split(":")
    if len(parts) != 2:
        return "bad headers", 0, 0

    try:
        chunk_no, total_chunks = [int(val.strip()) for val in parts]
    except ValueError:
        return "bad header value - chunk values should be numeric", 0, 0

    if not 0 < chunk_no <= total_chunks:
        return "bad header value - chunk range", 0, 0

    if request_chunk_no != chunk_no:
        return "bad header - value {chunk_no} is greater than chunk total", 0, 0

    return None, chunk_no, total_chunks


class OutboxHandler:
    # pylint: disable=too-many-arguments
    def __init__(self, config: EnvConfig = Depends(get_env_config), store: Store = Depends(get_store)):
        self.config = config
        self.store = store

    async def send_message(
        self,
        request: Request,
        sender_mailbox: AuthorisedMailbox,
        mex_headers: MexHeaders,
        content_encoding: str,
        accepts_api_version: int = 1,
    ):  # pylint: disable=too-many-locals

        if not mex_headers.mex_to:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="TO_DTS missing")

        if content_encoding and content_encoding != "gzip":
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail="UnsupportedContentEncoding"
            )

        chunk_error, chunk_no, total_chunks = get_chunk_range(cast(str, mex_headers.mex_chunk_range), 1)

        if chunk_error or chunk_no > 1:
            raise HTTPException(status_code=http_status.HTTP_417_EXPECTATION_FAILED, detail="Invalid chunk range")

        recipient = await self.store.get_mailbox(mex_headers.mex_to)
        if not recipient:
            raise HTTPException(status_code=http_status.HTTP_417_EXPECTATION_FAILED, detail="No mailbox matched")

        status = MessageStatus.ACCEPTED if total_chunks < 2 else MessageStatus.ACCEPTED

        message_id = uuid4().hex

        message = Message(
            events=[MessageEvent(status=status)],
            message_id=message_id,
            sender=MessageParty(
                mailbox_id=sender_mailbox.mailbox_id,
                mailbox_name=sender_mailbox.mailbox_name,
                ods_code=sender_mailbox.ods_code,
                org_code=sender_mailbox.org_code,
                org_name=sender_mailbox.org_name,
                billing_entity=sender_mailbox.billing_entity,
            ),
            recipient=MessageParty(
                mailbox_id=recipient.mailbox_id,
                mailbox_name=recipient.mailbox_name,
                ods_code=recipient.ods_code,
                org_code=recipient.org_code,
                org_name=recipient.org_name,
                billing_entity=recipient.billing_entity,
            ),
            total_chunks=total_chunks,
            message_type=MessageType.DATA,
            workflow_id=mex_headers.mex_workflow_id,
            metadata=MessageMetadata(
                subject=mex_headers.mex_subject,
                content_encoding=request.headers.get(Headers.Content_Encoding, ""),
                file_name=mex_headers.mex_filename or f"{message_id}.dat",
                local_id=mex_headers.mex_localid,
                partner_id=mex_headers.mex_partnerid,
                checksum=mex_headers.mex_content_checksum,
                encrypted=strtobool(mex_headers.mex_content_encrypted),
                is_compressed=strtobool(mex_headers.mex_content_compressed),
            ),
        )

        body = await request.body()
        if len(body) == 0:
            raise HTTPException(status_code=http_status.HTTP_417_EXPECTATION_FAILED, detail="MissingDataFile")

        await self.store.send_message(message, body)

        return send_message_response(message, accepts_api_version)

    async def _validate_chunk_upload(
        self,
        sender_mailbox: AuthorisedMailbox,
        message_id: str,
        chunk_number: int,
        chunk_range: Optional[str],
        content_encoding: str,
    ) -> Message:

        # why do we need to validate this ( or even accept it on a chunk upload ? )
        # total chunks is recorded on send message and chunk number is in the path,
        # think we can just remove this header on send_chunk completely
        chunk_range = (chunk_range or "").strip()
        if not chunk_range:
            raise HTTPException(status_code=http_status.HTTP_417_EXPECTATION_FAILED, detail="InvalidHeaderChunks")

        error, _, _ = get_chunk_range(chunk_range, chunk_number)
        if error:
            raise HTTPException(
                status_code=http_status.HTTP_417_EXPECTATION_FAILED,
                detail="InvalidHeaderChunks",
            )
        message: Optional[Message] = None

        if not message:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND)

        if not sender_mailbox or sender_mailbox.mailbox_id != message.sender.mailbox_id:
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN)

        if message.status != MessageStatus.UPLOADING:
            raise HTTPException(status_code=http_status.HTTP_423_LOCKED)

        if chunk_number > message.total_chunks or message.message_type != MessageType.DATA:
            raise HTTPException(status_code=http_status.HTTP_406_NOT_ACCEPTABLE)

        return message

    async def send_chunk(  # pylint: disable=too-many-locals
        self,
        request: Request,
        sender_mailbox: AuthorisedMailbox,
        message_id: str,
        chunk_number: int,
        mex_chunk_range: str,
        content_encoding: str,
        accepts_api_version: int = 1,
    ):

        chunk_range = (mex_chunk_range or "").strip()
        if not chunk_range:
            raise HTTPException(status_code=http_status.HTTP_417_EXPECTATION_FAILED, detail="InvalidHeaderChunks")

        error, _, _ = get_chunk_range(chunk_range, chunk_number)
        if error:
            raise HTTPException(
                status_code=http_status.HTTP_417_EXPECTATION_FAILED,
                detail="InvalidHeaderChunks",
            )
        message: Optional[Message] = None

        if not message:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND)

        if not sender_mailbox or sender_mailbox.mailbox_id != message.sender.mailbox_id:
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN)

        if message.status != MessageStatus.UPLOADING:
            raise HTTPException(status_code=http_status.HTTP_423_LOCKED)

        if chunk_number > message.total_chunks or message.message_type != MessageType.DATA:
            raise HTTPException(status_code=http_status.HTTP_406_NOT_ACCEPTABLE)

        await self.store.receive_chunk(message, chunk_number, await request.body())

        if chunk_number < message.total_chunks:
            return upload_chunk_response(message, chunk_number, accepts_api_version)

        await self.store.accept_message(message)

        return upload_chunk_response(message, chunk_number, accepts_api_version)

    async def rich_outbox(
        self,
        mailbox: AuthorisedMailbox,
        start_time: Optional[str],
        continue_from: Optional[str],
        max_results: int = 100,
    ) -> JSONResponse:

        from_date = datetime.utcnow() + relativedelta(days=-30)

        messages: Optional[list[Message]] = None
        last_evaluated_key: Optional[str] = None

        url_template = "{0}/outbox/rich"
        links: dict[str, str] = dict(
            self=get_handler_uri([mailbox.mailbox_id], url_template=url_template, start_time=from_date)
        )
        if last_evaluated_key:
            links["next"] = get_handler_uri(
                [mailbox.mailbox_id],
                url_template=url_template,
                start_time=from_date,
                continue_from="XXXX",
            )
        return get_rich_outbox_view(messages, links)
