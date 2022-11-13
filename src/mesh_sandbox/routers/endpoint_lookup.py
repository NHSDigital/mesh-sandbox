from fastapi import APIRouter, Depends, Path, status

from ..common import MESH_MEDIA_TYPES
from ..dependencies import get_accepts_api_version
from ..handlers.endpoint_lookup import EndPointLookupHandler
from ..views.lookup import EndpointLookupV1, MailboxLookupV2, endpoint_lookup_response
from .request_logging import RequestLoggingRoute

router = APIRouter(
    route_class=RequestLoggingRoute,
)


@router.get(
    "/{ods_code}/{workflow_id}",
    status_code=status.HTTP_200_OK,
    summary="Look up MESH address",
    responses={
        status.HTTP_200_OK: {
            "content": {
                MESH_MEDIA_TYPES[2]: {
                    "schema": MailboxLookupV2.schema(),
                },
                MESH_MEDIA_TYPES[1]: {
                    "schema": EndpointLookupV1.schema(),
                },
            }
        }
    },
    openapi_extra={"spec_order": 510},
)
async def get_receiving_mailbox_ids(
    ods_code: str = Path(..., title="ods_code", description="The ODS code of the organisation"),
    workflow_id: str = Path(..., title="workflow_id", description="The Workflow ID of the message"),
    accepts_api_version: int = Depends(get_accepts_api_version),
    handler: EndPointLookupHandler = Depends(EndPointLookupHandler),
):

    mailboxes = await handler.get_receiving_mailbox_ids(ods_code, workflow_id)

    endpoint_lookup_response(mailboxes, accepts_api_version)

    return await handler.get_receiving_mailbox_ids(
        ods_code=ods_code, workflow_id=workflow_id, accepts_api_version=accepts_api_version
    )
