from fastapi import APIRouter, Depends, Path, status

from ..common import MESH_MEDIA_TYPES
from ..dependencies import get_accepts_api_version
from ..handlers.lookup import LookupHandler
from ..views.lookup import EndpointLookupV1, MailboxLookupV2
from .request_logging import RequestLoggingRoute

router = APIRouter(
    route_class=RequestLoggingRoute,
)


@router.get(
    "/endpointlookup/{ods_code}/{workflow_id}",
    status_code=status.HTTP_200_OK,
    summary="Look up MESH address",
    responses={
        status.HTTP_200_OK: {
            "content": {
                MESH_MEDIA_TYPES[2]: {
                    "schema": MailboxLookupV2.model_json_schema(),
                },
                MESH_MEDIA_TYPES[1]: {
                    "schema": EndpointLookupV1.model_json_schema(),
                },
            }
        }
    },
    openapi_extra={"spec_order": 510},
)
async def lookup_by_ods_code_and_workflow_id(
    ods_code: str = Path(..., title="ods_code", description="The ODS code of the organisation"),
    workflow_id: str = Path(..., title="workflow_id", description="The Workflow ID of the message"),
    accepts_api_version: int = Depends(get_accepts_api_version),
    handler: LookupHandler = Depends(LookupHandler),
):
    return await handler.lookup_by_ods_code_and_workflow(ods_code, workflow_id, accepts_api_version)


@router.get(
    "/workflowsearch/{workflow_id}",
    summary="Lookup by workflow",
    responses={
        status.HTTP_200_OK: {
            "content": {
                MESH_MEDIA_TYPES[2]: {
                    "schema": MailboxLookupV2.model_json_schema(),
                }
            }
        }
    },
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
    openapi_extra={"spec_order": 511},
)
async def lookup_by_workflow_id(
    workflow_id: str = Path(..., title="workflow_id", description="The Workflow ID of the message"),
    accepts_api_version: int = Depends(get_accepts_api_version),
    handler: LookupHandler = Depends(LookupHandler),
):
    return await handler.lookup_by_workflow_id(workflow_id=workflow_id, accepts_api_version=accepts_api_version)
