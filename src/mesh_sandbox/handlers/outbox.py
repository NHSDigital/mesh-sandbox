from datetime import datetime
from typing import Optional, cast
from uuid import uuid4

from dateutil.parser import isoparse
from dateutil.relativedelta import relativedelta
from fastapi import Depends, HTTPException, Request
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from ..common import EnvConfig, constants, index_of, strtobool
from ..common.constants import Headers
from ..common.exceptions import MessagingException
from ..common.fernet import FernetHelper
from ..common.handler_helpers import get_handler_uri
from ..common.mex_headers import MexHeaders
from ..dependencies import get_env_config, get_fernet, get_store
from ..models.mailbox import Mailbox
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
    def __init__(
        self,
        config: EnvConfig = Depends(get_env_config),
        store: Store = Depends(get_store),
        fernet: FernetHelper = Depends(get_fernet),
    ):
        self.config = config
        self.store = store
        self.fernet = fernet

    async def send_message(
        self,
        request: Request,
        sender_mailbox: Mailbox,
        mex_headers: MexHeaders,
        content_encoding: str,
        accepts_api_version: int = 1,
    ):  # pylint: disable=too-many-locals

        if not mex_headers.mex_to:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=constants.ERROR_MISSING_TO_ADDRESS)

        if content_encoding and content_encoding != "gzip":
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail=constants.UNSUPPORTED_CONTENT_ENCODING
            )

        chunk_error, chunk_no, total_chunks = get_chunk_range(cast(str, mex_headers.mex_chunk_range), 1)

        if chunk_error or chunk_no > 1:
            raise HTTPException(
                status_code=http_status.HTTP_417_EXPECTATION_FAILED, detail=constants.ERROR_INVALID_HEADER_CHUNKS
            )

        recipient = await self.store.get_mailbox(mex_headers.mex_to)
        if not recipient:
            raise HTTPException(
                status_code=http_status.HTTP_417_EXPECTATION_FAILED, detail=constants.ERROR_UNREGISTERED_RECIPIENT
            )

        status = MessageStatus.ACCEPTED if total_chunks < 2 else MessageStatus.UPLOADING

        message_id = uuid4().hex.upper()

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

        if message.status == MessageStatus.ACCEPTED:
            message.file_size = len(body)

        await self.store.send_message(message, body)

        return send_message_response(message, accepts_api_version)

    async def send_chunk(  # pylint: disable=too-many-locals
        self,
        request: Request,
        sender_mailbox: Mailbox,
        message_id: str,
        chunk_number: int,
        mex_chunk_range: str,
        content_encoding: str,
        accepts_api_version: int = 1,
    ):

        chunk_range = (mex_chunk_range or "").strip()
        if not chunk_range:
            raise MessagingException(
                status_code=http_status.HTTP_417_EXPECTATION_FAILED,
                detail=constants.ERROR_INVALID_HEADER_CHUNKS,
                message_id=message_id,
            )

        error, _, _ = get_chunk_range(chunk_range, chunk_number)
        if error:
            raise MessagingException(
                status_code=http_status.HTTP_417_EXPECTATION_FAILED,
                detail=constants.ERROR_INVALID_HEADER_CHUNKS,
                message_id=message_id,
            )
        message: Optional[Message] = await self.store.get_message(message_id)

        if not message:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND)

        if not sender_mailbox or sender_mailbox.mailbox_id != message.sender.mailbox_id:
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN)

        if message.status != MessageStatus.UPLOADING:
            raise MessagingException(status_code=http_status.HTTP_423_LOCKED, message_id=message_id)

        if chunk_number > message.total_chunks or message.message_type != MessageType.DATA:
            raise MessagingException(status_code=http_status.HTTP_406_NOT_ACCEPTABLE, message_id=message_id)

        if (content_encoding or "").strip() != message.metadata.content_encoding:
            raise MessagingException(
                status_code=http_status.HTTP_417_EXPECTATION_FAILED,
                detail=constants.ERROR_CONTENT_ENCODING_CHANGED,
                message_id=message_id,
            )

        await self.store.receive_chunk(message, chunk_number, await request.body())

        if chunk_number < message.total_chunks:
            return upload_chunk_response(message, chunk_number, accepts_api_version)

        await self.store.accept_message(message)

        return upload_chunk_response(message, chunk_number, accepts_api_version)

    async def rich_outbox(
        self,
        mailbox: Mailbox,
        start_time: Optional[str],
        continue_from: Optional[str],
        max_results: int = 100,
    ) -> JSONResponse:
        max_results = max(min(max_results, 100), 0)
        from_date = datetime.utcnow() + relativedelta(days=-30) if start_time is None else isoparse(start_time)

        last_key: Optional[dict] = None
        if continue_from:
            last_key = self.fernet.decode_dict(continue_from)

        messages: list[Message] = cast(list[Message], await self.store.get_outbox(mailbox.mailbox_id))

        def message_filter(message: Message) -> bool:
            return message.created_timestamp > from_date

        messages = list(filter(message_filter, messages))

        if last_key:
            last_message_id = last_key["message_id"]
            ix = index_of(messages, (lambda msg: bool(msg.message_id == last_message_id)))
            if ix > -1:
                messages = messages[ix + 1 :]

        last_key = None

        if len(messages) > max_results:
            messages = messages[:max_results]
            if messages:
                last_key = {"message_id": messages[-1].message_id}

        url_template = "{0}/outbox/rich"
        links: dict[str, str] = {
            "self": get_handler_uri(
                [mailbox.mailbox_id], url_template=url_template, start_time=from_date, max_results=max_results
            )
        }
        if last_key:
            links["next"] = get_handler_uri(
                [mailbox.mailbox_id],
                url_template=url_template,
                start_time=from_date,
                max_results=max_results,
                continue_from=self.fernet.encode_dict(last_key),
            )
        return get_rich_outbox_view(messages, links)
