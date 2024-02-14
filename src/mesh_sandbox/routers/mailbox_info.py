from fastapi import APIRouter, Depends, Path, status

from ..common import MESH_MEDIA_TYPES
from ..handlers.mailbox_info import MailboxInfoHandler
from ..views.admin import MailboxDetails
from ..views.lookup import MailboxInfoView
from .request_logging import RequestLoggingRoute

router = APIRouter(
    route_class=RequestLoggingRoute,
)


@router.get(
    "/{mailbox_id}",
    summary="Get mailbox details.",
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
    responses={
        status.HTTP_200_OK: {
            "content": {
                MESH_MEDIA_TYPES[2]: {
                    "schema": MailboxInfoView.schema(),
                },
                MESH_MEDIA_TYPES[1]: {
                    "schema": MailboxInfoView.schema(),
                },
            }
        }
    },
    openapi_extra={"spec_order": 610},
)
async def get_mailbox_details(
    mailbox_id: str = Path(..., title="mailbox_id", description="The Mailbox ID of the mailbox to retrieve"),
    handler: MailboxInfoHandler = Depends(MailboxInfoHandler),
) -> MailboxDetails:
    mailbox = await handler.get_mailbox_details(mailbox_id)
    return mailbox
