from fastapi import APIRouter, Depends, Path, status

from ..common import MESH_MEDIA_TYPES
from ..dependencies import get_accepts_api_version
from ..handlers.workflow_search import WorkflowSearchHandler
from ..views.lookup import MailboxLookupV2
from .request_logging import RequestLoggingRoute

router = APIRouter(
    route_class=RequestLoggingRoute,
)


@router.get(
    "/{workflow_id}",
    summary="Lookup by workflow",
    responses={
        status.HTTP_200_OK: {
            "content": {
                MESH_MEDIA_TYPES[2]: {
                    "schema": MailboxLookupV2.schema(),
                }
            }
        }
    },
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
    openapi_extra={"spec_order": 511},
)
async def get_receiving_mailbox_ids(
    workflow_id: str = Path(..., title="workflow_id", description="The Workflow ID of the message"),
    accepts_api_version: int = Depends(get_accepts_api_version),
    handler: WorkflowSearchHandler = Depends(WorkflowSearchHandler),
):
    return await handler.get_receiving_mailbox_ids(workflow_id=workflow_id, accepts_api_version=accepts_api_version)
