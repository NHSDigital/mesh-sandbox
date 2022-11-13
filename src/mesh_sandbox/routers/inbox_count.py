from typing import cast
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response
from starlette.responses import JSONResponse

from ..common import MESH_MEDIA_TYPES, exclude_none_json_encoder
from ..dependencies import authorised_mailbox
from ..models.mailbox import AuthorisedMailbox
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
                    "schema": InboxCountV2.schema(),
                },
                MESH_MEDIA_TYPES[1]: {
                    "schema": InboxCountV1.schema(),
                },
            }
        }
    },
    response_model_exclude_none=True,
    openapi_extra={"spec_order": 290},
)
async def count_messages_in_inbox(request: Request):
    mailbox = cast(AuthorisedMailbox, request.state.authorised_mailbox)
    return JSONResponse(
        content=exclude_none_json_encoder(
            InboxCountV1(count=mailbox.inbox_count, internalID=uuid4().hex, allResultsIncluded=True)
        )
    )
