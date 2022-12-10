from typing import Optional, cast

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response
from starlette import status

from ..common import MESH_MEDIA_TYPES
from ..dependencies import (
    authorised_mailbox,
    get_accepts_api_version,
    normalise_message_id_path,
)
from ..handlers.inbox import DEFAULT_MAX_RESULTS, InboxHandler
from ..models.mailbox import Mailbox
from ..views.inbox import InboxV1, InboxV2, RichInboxView
from .request_logging import RequestLoggingRoute

router = APIRouter(
    dependencies=[Depends(authorised_mailbox)],
    route_class=RequestLoggingRoute,
)


@router.get(
    "",
    summary="Check an inbox",
    responses={
        status.HTTP_200_OK: {
            "content": {
                MESH_MEDIA_TYPES[2]: {"schema": InboxV2.schema()},
                MESH_MEDIA_TYPES[1]: {"schema": InboxV1.schema()},
            }
        },
        status.HTTP_403_FORBIDDEN: {"description": "Authentication failed", "content": None},
    },
    response_model_exclude_none=True,
    openapi_extra={"spec_order": 200},
)
async def list_messages(
    request: Request,
    max_results: int = Query(
        default=DEFAULT_MAX_RESULTS,
        title="Max results",
        description="maximum results to return when using accept: application/vnd.mesh.v2+json "
        "if more results exist, 'links.next' will be populated",
        example="100",
        ge=10,
        le=5000,
    ),
    continue_from: str = Query(
        default=None,
        title="Continue From",
        description="if more results exist than 'max_results', use continue_from to "
        "continue retrieving results from links.next",
        examples={
            f"accept: {MESH_MEDIA_TYPES[2]}": {
                "value": "eyJwayI6ICJNQiNNU0cjTUIjMTIzNEhDMTIzNCMiLCAic2siOiAiTUIjT"
                "VNHIzIwMjIwMjI4MTc0MzIzMTIzX0FDREVEMSMifQ%3D%3D"
            },
            f"accept: {MESH_MEDIA_TYPES[1]}": {"value": "20220228174323123_ACDED1"},
        },
        min_length=24,
        max_length=1000,
    ),
    workflow_filter: str = Query(
        default=None,
        title="Workflow Id filter",
        description="""filter inbox by workflow id, conditions:
* equals: =WORKFLOW1
* does not equal: =!WORKFLOW1
* begins with: =WORKFL\\*
* does not begin with: =!WORKFL\\*
* contains: =\\*_ACK\\*
* does not contain: =!\\*_ACK\\*""",
        example="!*_ACK*",
        min_length=2,
        max_length=255,
    ),
    accepts_api_version: int = Depends(get_accepts_api_version),
    handler: InboxHandler = Depends(InboxHandler),
):
    return await handler.list_messages(
        cast(Mailbox, request.state.authorised_mailbox),
        accepts_api_version,
        max_results,
        continue_from,
        workflow_filter,
    )


@router.put(
    "/{message_id}/status/acknowledged",
    summary="Acknowledge message",
    responses={
        status.HTTP_200_OK: {"content": None},
        status.HTTP_403_FORBIDDEN: {"description": "Authentication failed", "content": None},
    },
    response_model_exclude_none=True,
    openapi_extra={"spec_order": 220},
)
async def acknowledge_message(
    request: Request,
    message_id: str = Depends(normalise_message_id_path),
    accepts_api_version: int = Depends(get_accepts_api_version),
    handler: InboxHandler = Depends(InboxHandler),
):
    return await handler.acknowledge_message(
        cast(Mailbox, request.state.authorised_mailbox), message_id, accepts_api_version
    )


@router.head(
    "/{message_id}",
    summary="Head Message",
    responses={
        status.HTTP_200_OK: {
            "content": None,
        },
        status.HTTP_404_NOT_FOUND: {"description": "Not Found, messages does not exist", "content": None},
        status.HTTP_410_GONE: {"description": "Gone, message has expired or otherwise failed", "content": None},
        status.HTTP_403_FORBIDDEN: {"description": "Authentication failed", "content": None},
    },
    response_model_exclude_none=True,
    openapi_extra={"spec_order": 211},
)
async def head_message(
    request: Request,
    message_id: str = Depends(normalise_message_id_path),
    handler: InboxHandler = Depends(InboxHandler),
):
    return await handler.head_message(cast(Mailbox, request.state.authorised_mailbox), message_id)


@router.get(
    "/rich",  # must declare this above retrieve_message to avoid conflict
    response_class=Response,
    summary="Rich Inbox",
    responses={
        status.HTTP_200_OK: {
            "content": {
                MESH_MEDIA_TYPES[2]: {
                    "schema": RichInboxView.schema(),
                }
            },
        }
    },
    include_in_schema=False,
    response_model_exclude_none=True,
    openapi_extra={"spec_order": 250},
)
async def rich_inbox(
    request: Request,
    start_time: Optional[str] = Query(
        default=None,
        title="start_time",
        description="ISO8601 formatted date and time. If not supplied, defaults to 30 days ago",
        example="2022-05-20T14:35:52Z",
    ),
    continue_from: str = Query(
        default=None,
        title="Continue From",
        description="if more results exist than 'max_results', use continue_from to continue retrieving results",
        example=(
            "eyJwayI6ICJNQiNNU0cjTUIjMTIzNEhDMTIzNCMiLCAic2siOiAiTUIjTVNHIzIwMj"
            "IwMjI4MTc0MzIzMTIzX0FDREVEMSMifQ%3D%3D"
        ),
        min_length=24,
        max_length=1000,
        include_in_schema=False,
    ),
    max_results: int = Query(
        default=100,
        title="Max Results",
        description="max results to retrieve in one go",
        example="100",
        le=2000,
        ge=1,
        include_in_schema=False,
    ),
    handler: InboxHandler = Depends(InboxHandler),
):
    return await handler.rich_inbox(
        cast(Mailbox, request.state.authorised_mailbox), start_time, continue_from, max_results
    )


@router.get(
    "/{message_id}",
    summary="Download message",
    response_class=Response,
    responses={
        status.HTTP_200_OK: {
            "description": "OK, full message retrieved",
            "content": {"application/octet-stream": None},
        },
        status.HTTP_206_PARTIAL_CONTENT: {
            "description": (
                "Partial Content – Indicates that chunk has been downloaded "
                "successfully and that there are further chunks."
            ),
            "content": {"application/octet-stream": None},
        },
        status.HTTP_404_NOT_FOUND: {"description": "Not Found, messages does not exist", "content": None},
        status.HTTP_410_GONE: {"description": "Gone, message has expired or otherwise failed", "content": None},
        status.HTTP_403_FORBIDDEN: {"description": "Authentication failed", "content": None},
    },
    response_model_exclude_none=True,
    openapi_extra={"spec_order": 210},
)
async def retrieve_message(
    request: Request,
    message_id: str = Depends(normalise_message_id_path),
    accept_encoding: str = Header(
        title="Accept-Encoding",
        default="",
        example="gzip",
    ),
    accepts_api_version: int = Depends(get_accepts_api_version),
    handler: InboxHandler = Depends(InboxHandler),
):
    return await handler.retrieve_message(
        cast(Mailbox, request.state.authorised_mailbox), message_id, accept_encoding, accepts_api_version
    )


@router.get(
    "/{message_id}/{chunk_number}",
    summary="Download message chunk",
    response_class=Response,
    responses={
        status.HTTP_200_OK: {
            "description": "OK - chunk downloaded and no further chunks exist",
            "content": {"application/octet-stream": None},
        },
        status.HTTP_206_PARTIAL_CONTENT: {
            "description": (
                "Partial Content – Indicates that chunk has been downloaded "
                "successfully and that there are further chunks."
            ),
            "content": {"application/octet-stream": None},
        },
    },
    response_model_exclude_none=True,
    openapi_extra={"spec_order": 230},
)
async def retrieve_chunk(
    request: Request,
    message_id: str = Depends(normalise_message_id_path),
    chunk_number: int = Path(..., title="chunk_number", description="The index number of the chunk", example="1", ge=1),
    accept_encoding: str = Header(
        title="Accept-Encoding",
        default="",
        example="gzip",
    ),
    accepts_api_version: int = Depends(get_accepts_api_version),
    handler: InboxHandler = Depends(InboxHandler),
):
    return await handler.retrieve_chunk(
        cast(Mailbox, request.state.authorised_mailbox),
        message_id,
        accept_encoding,
        chunk_number=chunk_number,
        accepts_api_version=accepts_api_version,
    )
