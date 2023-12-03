from typing import cast
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response
from starlette.responses import JSONResponse

from ..common import MESH_MEDIA_TYPES, exclude_none_json_encoder
from ..dependencies import authorised_mailbox, get_accepts_api_version
from ..models.mailbox import Mailbox
from ..views.inbox import InboxCountV1, InboxCountV2
from .request_logging import RequestLoggingRoute

router = APIRouter(
    dependencies=[Depends(authorised_mailbox)],
    route_class=RequestLoggingRoute,
)


@router.get(
    "",
    summary="Check an inbox count (deprecated)",
    response_class=Response,
    responses={
        200: {
            "content": {
                MESH_MEDIA_TYPES[2]: {
                    "schema": InboxCountV2.model_json_schema(),
                },
                MESH_MEDIA_TYPES[1]: {
                    "schema": InboxCountV1.model_json_schema(),
                },
            }
        }
    },
    deprecated=True,
    response_model_exclude_none=True,
    openapi_extra={"spec_order": 290},
)
async def count_messages_in_inbox(
    request: Request,
    accepts_api_version: int = Depends(get_accepts_api_version),
):
    mailbox = cast(Mailbox, request.state.authorised_mailbox)

    count = mailbox.inbox_count or 0

    response = (
        InboxCountV1(count=count, internalID=uuid4().hex, allResultsIncluded=True)
        if accepts_api_version < 2
        else InboxCountV2(count=count)
    )

    return JSONResponse(content=exclude_none_json_encoder(response))
