from typing import Optional, cast

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    Path,
    Query,
    Request,
    Response,
    status,
)

from ..common import MESH_MEDIA_TYPES
from ..common.constants import Headers
from ..common.mex_headers import MexHeaders, send_message_mex_headers
from ..dependencies import (
    authorised_mailbox,
    get_accepts_api_version,
    normalise_content_encoding,
    normalise_content_type,
    normalise_message_id_path,
)
from ..handlers.outbox import OutboxHandler
from ..models.mailbox import Mailbox
from ..views.outbox import RichOutboxView, SendMessageV1, SendMessageV2
from .request_logging import RequestLoggingRoute

router = APIRouter(
    dependencies=[Depends(authorised_mailbox)],
    route_class=RequestLoggingRoute,
)


@router.post(
    "",
    summary="Send message",
    responses={
        status.HTTP_202_ACCEPTED: {
            "content": {
                MESH_MEDIA_TYPES[2]: {
                    "schema": SendMessageV2.model_json_schema(),
                },
                MESH_MEDIA_TYPES[1]: {
                    "schema": SendMessageV1.model_json_schema(),
                },
            }
        },
        status.HTTP_417_EXPECTATION_FAILED: {"content": None},
    },
    status_code=status.HTTP_202_ACCEPTED,
    response_model_exclude_none=True,
    openapi_extra={"spec_order": 300},
)
async def send_message(
    background_tasks: BackgroundTasks,
    request: Request,
    mex_headers: MexHeaders = Depends(send_message_mex_headers),
    content_type: str = Depends(normalise_content_type),
    content_encoding: str = Depends(normalise_content_encoding),
    accepts_api_version: int = Depends(get_accepts_api_version),
    handler: OutboxHandler = Depends(OutboxHandler),
):
    return await handler.send_message(
        background_tasks=background_tasks,
        request=request,
        sender_mailbox=cast(Mailbox, request.state.authorised_mailbox),
        mex_headers=mex_headers,
        content_encoding=content_encoding,
        content_type=content_type,
        accepts_api_version=accepts_api_version,
    )


@router.post(
    "/{message_id}/{chunk_number}",
    summary="Send chunked message",
    responses={202: {"content": None}},
    status_code=status.HTTP_202_ACCEPTED,
    response_model_exclude_none=True,
    openapi_extra={"spec_order": 310},
)
async def send_chunk(
    background_tasks: BackgroundTasks,
    request: Request,
    message_id: str = Depends(normalise_message_id_path),
    mex_chunk_range: str = Header(title=Headers.Mex_Chunk_Range, default="", example="1:2", max_length=20),
    content_encoding: str = Depends(normalise_content_encoding),
    chunk_number: int = Path(..., title="chunk_number", description="The index number of the chunk", example="1"),
    accepts_api_version: int = Depends(get_accepts_api_version),
    handler: OutboxHandler = Depends(OutboxHandler),
):
    return await handler.send_chunk(
        background_tasks=background_tasks,
        request=request,
        sender_mailbox=cast(Mailbox, request.state.authorised_mailbox),
        message_id=message_id,
        chunk_number=chunk_number,
        mex_chunk_range=mex_chunk_range,
        content_encoding=content_encoding,
        accepts_api_version=accepts_api_version,
    )


@router.get(
    "/rich",
    summary="Rich Outbox",
    response_class=Response,
    responses={
        200: {
            "content": {
                MESH_MEDIA_TYPES[2]: {
                    "schema": RichOutboxView.model_json_schema(),
                }
            }
        }
    },
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    response_model_exclude_none=True,
    openapi_extra={"spec_order": 340},
)
async def rich_outbox(
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
            "eyJwayI6ICJNQiNNU0cjTUIjMTIzNEhDMTIzNCMiLCAic2siOiAiTUIj"
            "TVNHIzIwMjIwMjI4MTc0MzIzMTIzX0FDREVEMSMifQ%3D%3D"
        ),
        min_length=24,
        max_length=1000,
        include_in_schema=False,
    ),
    max_results: int = Query(
        default=100,
        title="Max results",
        description="maximum results to return when using accept: application/vnd.mesh.v2+json "
        "if more results exist, 'links.next' will be populated",
        example="100",
        ge=10,
        le=5000,
    ),
    handler: OutboxHandler = Depends(OutboxHandler),
):
    return await handler.rich_outbox(
        cast(Mailbox, request.state.authorised_mailbox), start_time, continue_from, max_results
    )
