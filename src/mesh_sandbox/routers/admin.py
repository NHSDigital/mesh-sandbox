from fastapi import APIRouter, Depends, status

from ..dependencies import EnvConfig, get_env_config, normalise_mailbox_id_path
from ..handlers.admin import AdminHandler
from ..views.admin import PutReportRequest
from .request_logging import RequestLoggingRoute

router = APIRouter(
    route_class=RequestLoggingRoute,
)

TESTING_ONLY = "This is not part of the real api!, just for testing purposes"


@router.get("/health", status_code=status.HTTP_200_OK, include_in_schema=False, response_model_exclude_none=True)
@router.get("/_status", status_code=status.HTTP_200_OK, include_in_schema=False, response_model_exclude_none=True)
@router.get("/_ping", status_code=status.HTTP_200_OK, include_in_schema=False, response_model_exclude_none=True)
@router.get("/_ping", status_code=status.HTTP_200_OK, include_in_schema=False, response_model_exclude_none=True)
@router.get("/healthcheck", status_code=status.HTTP_200_OK, include_in_schema=False, response_model_exclude_none=True)
@router.get(
    "/messageexchange/_ping", status_code=status.HTTP_200_OK, include_in_schema=False, response_model_exclude_none=True
)
@router.get(
    "/messageexchange/deepping",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    response_model_exclude_none=True,
)
async def ping(config: EnvConfig = Depends(get_env_config)):
    return {"env": config.env, "build_label": config.build_label, "status": "running", "outcome": "Yes"}


@router.delete(
    "/admin/reset",
    summary=f"Reset in memory storage completely, will reload from disk. {TESTING_ONLY}",
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
)
@router.delete(
    "/messageexchange/reset",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    response_model_exclude_none=True,
)
async def reset(
    handler: AdminHandler = Depends(AdminHandler),
):
    await handler.reset()
    return {"message": "all mailboxes reset"}


@router.delete(
    "/admin/reset/{mailbox_id}",
    summary=f"Clear messages in a particular inbox. {TESTING_ONLY}",
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
)
@router.delete(
    "/messageexchange/reset/{mailbox_id}",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    response_model_exclude_none=True,
)
async def reset_mailbox(
    mailbox_id: str = Depends(normalise_mailbox_id_path),
    handler: AdminHandler = Depends(AdminHandler),
):
    await handler.reset(mailbox_id)
    return {"message": f"mailbox {mailbox_id} reset"}


@router.post(
    "/messageexchange/report",
    summary=f"Put a report messages into a particular inbox. {TESTING_ONLY}",
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
)
async def put_report(
    request: PutReportRequest,
    handler: AdminHandler = Depends(AdminHandler),
):
    message = await handler.put_report(request)
    return {"message_id": message.message_id}
