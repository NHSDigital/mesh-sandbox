from typing import cast

from fastapi import APIRouter, Depends, Path, Request, status

from ..common import MESH_MEDIA_TYPES
from ..dependencies import (
    authorised_mailbox,
    get_accepts_api_version,
    normalise_message_id_query,
)
from ..handlers.tracking import TrackingHandler
from ..models.mailbox import Mailbox
from ..views.tracking import TrackingV1, TrackingV2
from .request_logging import RequestLoggingRoute

router = APIRouter(
    dependencies=[Depends(authorised_mailbox)],
    route_class=RequestLoggingRoute,
)


@router.get(
    "/tracking",
    summary="Track outbox",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "content": {
                MESH_MEDIA_TYPES[2]: {
                    "schema": TrackingV2.schema(),
                },
                MESH_MEDIA_TYPES[1]: {
                    "schema": TrackingV1.schema(),
                },
            }
        }
    },
    response_model_exclude_none=True,
    openapi_extra={"spec_order": 411},
)
async def tracking_by_message_id(
    request: Request,
    message_id: str = Depends(normalise_message_id_query),
    accepts_api_version: int = Depends(get_accepts_api_version),
    handler: TrackingHandler = Depends(TrackingHandler),
):
    return await handler.tracking_by_message_id(
        sender_mailbox=cast(Mailbox, request.state.authorised_mailbox),
        message_id=message_id,
        accepts_api_version=accepts_api_version,
    )


@router.get(
    "/tracking/{local_id}",
    summary="Track outbox (deprecated)",
    deprecated=True,
    status_code=status.HTTP_200_OK,
    response_model=TrackingV1,
    response_model_exclude_none=True,
    openapi_extra={"spec_order": 490},
)
async def tracking_by_local_id(
    request: Request,
    local_id: str = Path(
        ...,
        title="The local ID of the message",
        description="The user supplied (local ID) of the message",
        example="api-docs-bob-sends-alice-a-chunked-file",
        min_length=1,
    ),
    handler: TrackingHandler = Depends(TrackingHandler),
):
    return await handler.tracking_by_local_id(
        sender_mailbox=cast(Mailbox, request.state.authorised_mailbox), local_id=local_id
    )
