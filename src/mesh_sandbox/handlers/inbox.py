import gzip
from datetime import datetime, tzinfo
from typing import Any, Callable, Optional, cast

from dateutil.parser import isoparse
from dateutil.relativedelta import relativedelta
from dateutil.tz import tzutc
from fastapi import BackgroundTasks, Depends, HTTPException, Response, status
from starlette.responses import JSONResponse

from ..common import MESH_MEDIA_TYPES, constants, exclude_none_json_encoder, index_of
from ..common.constants import Headers
from ..common.fernet import FernetHelper
from ..common.handler_helpers import get_handler_uri
from ..common.messaging import Messaging
from ..dependencies import get_fernet, get_messaging
from ..models.mailbox import Mailbox
from ..models.message import Message, MessageDeliveryStatus, MessageStatus, MessageType
from ..views.inbox import InboxV1, InboxV2, get_rich_inbox_view

HTTP_DATETIME_FORMAT = "%a, %d %b %Y %H:%M:%S %Z"
DEFAULT_MAX_RESULTS = 500


def to_http_datetime(maybe_naive_dt: datetime, as_timezone: Optional[tzinfo] = None) -> str:
    if maybe_naive_dt.tzinfo:
        return maybe_naive_dt.strftime(HTTP_DATETIME_FORMAT)
    as_timezone = as_timezone or tzutc()
    maybe_naive_dt = maybe_naive_dt.astimezone(tz=as_timezone)
    return maybe_naive_dt.strftime(HTTP_DATETIME_FORMAT)


class InboxHandler:
    def __init__(
        self,
        messaging: Messaging = Depends(get_messaging),
        fernet: FernetHelper = Depends(get_fernet),
    ):
        self.messaging = messaging

        self.fernet = fernet

    @staticmethod
    def _get_status_headers(message: Message) -> dict[str, Optional[str]]:
        status_timestamp = (
            message.status_timestamp(MessageStatus.ACCEPTED, MessageStatus.ERROR) or datetime.utcnow()
        ).strftime("%Y%m%d%H%M%S")

        error_event = message.error_event

        if message.message_type == MessageType.DATA and not error_event:
            return {
                Headers.Mex_StatusCode: "00",
                Headers.Mex_StatusEvent: "TRANSFER",
                Headers.Mex_StatusDescription: "Transferred to recipient mailbox",
                Headers.Mex_StatusSuccess: MessageDeliveryStatus.SUCCESS,
                Headers.Mex_StatusTimestamp: status_timestamp,
            }

        if not error_event:
            return {
                Headers.Mex_StatusSuccess: MessageDeliveryStatus.ERROR,
                Headers.Mex_StatusTimestamp: status_timestamp,
            }

        return {
            Headers.Mex_LinkedMsgId: error_event.linked_message_id,
            Headers.Mex_StatusCode: error_event.code,
            Headers.Mex_StatusEvent: error_event.event,
            Headers.Mex_StatusDescription: error_event.description,
            Headers.Mex_StatusSuccess: MessageDeliveryStatus.ERROR,
            Headers.Mex_StatusTimestamp: status_timestamp,
        }

    @staticmethod
    def _get_response_headers(message: Message, chunk_number: int):
        headers = {
            Headers.Mex_From: message.sender.mailbox_id,
            Headers.Mex_To: message.recipient.mailbox_id,
            Headers.Mex_WorkflowID: message.workflow_id,
            Headers.Mex_Chunk_Range: f"{chunk_number}:{message.total_chunks}",
            Headers.Mex_Total_Chunks: f"{message.total_chunks or 0}",
            Headers.Mex_AddressType: "ALL",
            Headers.Mex_LocalID: message.metadata.local_id,
            Headers.Mex_PartnerID: message.metadata.partner_id,
            Headers.Mex_FileName: message.metadata.file_name or f"{message.message_id}.dat",
            Headers.Mex_Subject: message.metadata.subject,
            Headers.Mex_Version: "1.0",
            Headers.Mex_MessageType: message.message_type,
            Headers.Mex_MessageID: message.message_id,
            Headers.Content_Encoding: message.metadata.content_encoding,
            **InboxHandler._get_status_headers(message),
            Headers.Mex_Content_Compressed: "Y" if message.metadata.compressed else None,
            Headers.Mex_Content_Encrypted: "Y" if message.metadata.encrypted else None,
            Headers.Mex_Content_Checksum: message.metadata.checksum,
            Headers.Mex_Content_Type: message.metadata.content_type,
        }

        if message.message_type == MessageType.REPORT:
            headers.pop(Headers.Content_Encoding)

        if message.last_event and message.last_event.timestamp:
            headers[Headers.Last_Modified] = to_http_datetime(message.last_event.timestamp)

        # filter empty headers ( as per existing API )
        return {h: v for h, v in headers.items() if v}

    async def head_message(self, mailbox: Mailbox, message_id: str):
        message = await self.messaging.get_message(message_id)

        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=constants.ERROR_MESSAGE_DOES_NOT_EXIST)

        is_recipient_query = message.recipient.mailbox_id == mailbox.mailbox_id
        is_sender_query = message.sender and message.sender.mailbox_id == mailbox.mailbox_id
        allow_access = is_recipient_query or is_sender_query

        if not allow_access:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=constants.ERROR_MESSAGE_DOES_NOT_EXIST)

        allowed_statuses = (
            (MessageStatus.ACCEPTED, MessageStatus.ACKNOWLEDGED) if is_recipient_query else MessageStatus.VALID_VALUES
        )

        if message.status not in allowed_statuses:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail=constants.ERROR_MESSAGE_GONE)

        headers = self._get_response_headers(message, 1)
        return Response(headers=headers)

    async def retrieve_message(
        self, mailbox: Mailbox, message_id: str, accept_encoding: str, accepts_api_version: int = 1
    ):
        return await self._retrieve_message_or_chunk(
            mailbox=mailbox,
            message_id=message_id,
            accept_encoding=accept_encoding,
            accepts_api_version=accepts_api_version,
        )

    async def retrieve_chunk(
        self, mailbox: Mailbox, message_id: str, accept_encoding: str, chunk_number: int, accepts_api_version: int = 1
    ):
        return await self._retrieve_message_or_chunk(
            mailbox=mailbox,
            message_id=message_id,
            accept_encoding=accept_encoding,
            chunk_number=chunk_number,
            accepts_api_version=accepts_api_version,
        )

    async def _retrieve_message_or_chunk(
        self,
        mailbox: Mailbox,
        message_id: str,
        accept_encoding: str,
        chunk_number: int = 1,
        accepts_api_version: int = 1,
    ):
        message = await self.messaging.get_message(message_id)

        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=constants.ERROR_MESSAGE_DOES_NOT_EXIST)

        if message.recipient.mailbox_id != mailbox.mailbox_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        if message.status not in (MessageStatus.ACCEPTED, MessageStatus.ACKNOWLEDGED):
            raise HTTPException(status_code=status.HTTP_410_GONE, detail=constants.ERROR_MESSAGE_GONE)

        headers = self._get_response_headers(message, chunk_number)

        if message.message_type != MessageType.DATA:
            return Response(headers=headers, content="")

        if chunk_number < 1 or chunk_number > message.total_chunks:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=constants.ERROR_MESSAGE_DOES_NOT_EXIST)

        status_code = status.HTTP_200_OK if chunk_number >= message.total_chunks else status.HTTP_206_PARTIAL_CONTENT

        chunk = await self.messaging.get_chunk(message, chunk_number)

        if chunk is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=constants.ERROR_MESSAGE_DOES_NOT_EXIST)

        headers[Headers.Content_Length] = str(len(chunk))
        content_encoding = headers.get(Headers.Content_Encoding, "")
        if content_encoding == "gzip" and "gzip" not in accept_encoding:
            headers.pop(Headers.Content_Encoding)
            chunk = gzip.decompress(chunk)

        if accepts_api_version > 1 and not content_encoding and "gzip" in accept_encoding:
            headers[Headers.Content_Encoding] = "gzip"
            chunk = gzip.compress(chunk)

        headers[Headers.Content_Length] = str(len(chunk))

        if headers.get(Headers.Content_Encoding) == "gzip":
            headers[Headers.Mex_Content_Compressed] = "Y"

        media_type = "application/octet-stream"
        if accepts_api_version > 1 and message.total_chunks < 2 and message.metadata.content_type:
            media_type = message.metadata.content_type

        return Response(
            status_code=status_code,
            content=chunk,
            headers=headers,
            media_type=media_type,
        )

    async def acknowledge_message(
        self, background_tasks: BackgroundTasks, mailbox: Mailbox, message_id: str, accepts_api_version: int = 1
    ):
        message = await self.messaging.get_message(message_id)
        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=constants.ERROR_MESSAGE_DOES_NOT_EXIST)

        if message.recipient.mailbox_id != mailbox.mailbox_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        def response():
            if accepts_api_version < 2:
                # current format compatibility
                return {"messageId": message.message_id}  # type: ignore[union-attr]
            return Response()

        if message.status != MessageStatus.ACCEPTED:
            return response()

        await self.messaging.acknowledge_message(message=message, background_tasks=background_tasks)

        return response()

    async def _get_inbox_messages(
        self,
        mailbox: Mailbox,
        max_results: int = DEFAULT_MAX_RESULTS,
        last_key: Optional[dict] = None,
        message_filter: Optional[Callable[[Message], bool]] = None,
        rich: bool = False,
    ) -> tuple[list[Message], Optional[dict]]:
        messages = (
            sorted(
                await self.messaging.get_inbox_messages(mailbox.mailbox_id),
                key=lambda message: message.created_timestamp,
                reverse=True,
            )
            if rich
            else await self.messaging.get_accepted_inbox_messages(mailbox.mailbox_id)
        )

        if message_filter:
            messages = list(filter(message_filter, messages))

        if last_key:
            last_message_id = last_key["message_id"]
            ix = index_of(messages, lambda msg: bool(msg.message_id == last_message_id))
            if ix > -1:
                messages = messages[ix + 1 :]

        last_key = None

        if len(messages) > max_results:
            messages = messages[:max_results]
            if messages:
                last_key = {"message_id": messages[-1].message_id}

        return messages, last_key

    @staticmethod
    def _get_workflow_filter(workflow_filter: Optional[str]) -> Optional[Callable[[Message], bool]]:  # noqa: C901
        workflow_id_filter = (workflow_filter or "").strip()
        if not workflow_id_filter:
            return None

        is_not = workflow_id_filter.startswith("!")
        if is_not:
            workflow_id_filter = workflow_id_filter[1:]

        is_contains = workflow_id_filter.startswith("*")
        if is_contains:
            workflow_id_filter = workflow_id_filter[1:-1]

        is_begins_with = workflow_id_filter.endswith("*")
        if is_begins_with:
            workflow_id_filter = workflow_id_filter[:-1]

        if not is_not and not is_contains and not is_begins_with:

            def _is_exact(message: Message) -> bool:
                return message.workflow_id == workflow_id_filter

            return _is_exact

        if not is_contains and not is_begins_with:

            def _is_not_exact(message: Message) -> bool:
                return message.workflow_id != workflow_id_filter

            return _is_not_exact

        if is_begins_with:

            def _begins_with(message: Message) -> bool:
                return message.workflow_id.startswith(workflow_id_filter)

            def _not_begins_with(message: Message) -> bool:
                return not message.workflow_id.startswith(workflow_id_filter)

            if is_not:
                return _not_begins_with
            return _begins_with

        def _contains(message: Message) -> bool:
            return workflow_id_filter in message.workflow_id

        def _not_contains(message: Message) -> bool:
            return workflow_id_filter not in message.workflow_id

        if is_not:
            return _not_contains
        return _contains

    async def list_messages(
        self,
        mailbox: Mailbox,
        accepts_api_version: int = 1,
        max_results: int = DEFAULT_MAX_RESULTS,
        continue_from: Optional[str] = None,
        workflow_filter: Optional[str] = None,
    ) -> Response:
        last_key: Optional[dict] = None

        if continue_from:
            if accepts_api_version < 2:
                last_key = {"message_id": continue_from}
            else:
                last_key = self.fernet.decode_dict(continue_from)

        message_filter = self._get_workflow_filter(workflow_filter)

        messages, last_key = await self._get_inbox_messages(mailbox, max_results, last_key, message_filter)

        if accepts_api_version < 2:
            return JSONResponse(
                content=exclude_none_json_encoder(InboxV1(messages=[msg.message_id for msg in messages])),
                media_type=MESH_MEDIA_TYPES[1],
            )

        response = {"messages": [msg.message_id for msg in messages]}

        uri_query_args = {
            "max_results": max_results if max_results != DEFAULT_MAX_RESULTS else None,
            "workflow_filter": workflow_filter,
        }

        links: dict[str, str] = {"self": get_handler_uri([mailbox.mailbox_id], "{0}/inbox", **uri_query_args)}

        result: dict[str, Any] = {
            "messages": cast(list[str], response.get("messages", [])),
            "approx_inbox_count": mailbox.inbox_count,
            "links": links,
        }

        if last_key:
            uri_query_args["continue_from"] = self.fernet.encode_dict(last_key)
            links["next"] = get_handler_uri([mailbox.mailbox_id], "{0}/inbox", **uri_query_args)

        return JSONResponse(content=exclude_none_json_encoder(InboxV2(**result)), media_type=MESH_MEDIA_TYPES[2])

    async def rich_inbox(
        self,
        mailbox: Mailbox,
        start_time: Optional[str],
        continue_from: Optional[str],
        max_results: int = 100,
    ) -> JSONResponse:
        last_key: Optional[dict] = None
        if continue_from:
            last_key = self.fernet.decode_dict(continue_from)

        from_date = datetime.utcnow() + relativedelta(days=-30) if start_time is None else isoparse(start_time)

        def message_filter(message: Message) -> bool:
            return message.created_timestamp > from_date

        messages, last_key = await self._get_inbox_messages(mailbox, max_results, last_key, message_filter, rich=True)

        url_template = "{0}/inbox/rich"
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
        return get_rich_inbox_view(messages, links)
