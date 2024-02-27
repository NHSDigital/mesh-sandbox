from fastapi import APIRouter, BackgroundTasks, Depends, Path, Response, status

from ..dependencies import (
    EnvConfig,
    get_env_config,
    normalise_mailbox_id_path,
    normalise_message_id_path,
)
from ..handlers.admin import AdminHandler
from ..views.admin import (
    AddMessageEventRequest,
    CreateReportRequest,
    MailboxDetails,
    MessageDetails,
)
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
    "/messageexchange/admin/reset",
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
    "/messageexchange/admin/reset/{mailbox_id}",
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
    "/messageexchange/admin/report",
    summary=f"Put a report messages into a particular inbox. {TESTING_ONLY}",
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
)
async def create_report(
    new_report: CreateReportRequest,
    background_tasks: BackgroundTasks,
    handler: AdminHandler = Depends(AdminHandler),
):
    message = await handler.create_report(new_report, background_tasks)
    return {"message_id": message.message_id}


@router.post(
    "/admin/message/{message_id}/event",
    summary=f"appends a status event to a given message, if exists. {TESTING_ONLY}",
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
)
@router.post(
    "/messageexchange/admin/message/{message_id}/event",
    summary=f"appends a status event to a given message, if exists. {TESTING_ONLY}",
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
)
async def add_message_event(
    new_event: AddMessageEventRequest,
    background_tasks: BackgroundTasks,
    message_id: str = Depends(normalise_message_id_path),
    handler: AdminHandler = Depends(AdminHandler),
):
    await handler.add_message_event(message_id, new_event, background_tasks)
    return Response()


@router.get(
    "/admin/mailbox/{mailbox_id}",
    summary=f"Get mailbox details. {TESTING_ONLY}",
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
)
@router.get(
    "/messageexchange/admin/mailbox/{mailbox_id}",
    summary=f"Get mailbox details. {TESTING_ONLY}",
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
)
@router.get(
    "/messageexchange/mailbox/{mailbox_id}",
    summary="Get mailbox details.",
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
)
async def get_mailbox_details(
    mailbox_id: str = Path(..., title="mailbox_id", description="The Mailbox ID of the mailbox to retrieve"),
    handler: AdminHandler = Depends(AdminHandler),
) -> MailboxDetails:
    mailbox = await handler.get_mailbox_details(mailbox_id)
    return mailbox


@router.get(
    "/admin/message/{message_id}",
    summary=f"Get message details matching id from message store. {TESTING_ONLY}",
    status_code=status.HTTP_200_OK,
    response_model=MessageDetails,
    response_model_exclude_none=True,
)
@router.get(
    "/messageexchange/admin/message/{message_id}",
    summary=f"Get message details matching id from message store. {TESTING_ONLY}",
    status_code=status.HTTP_200_OK,
    response_model=MessageDetails,
    response_model_exclude_none=True,
)
async def get_message_details(
    message_id: str = Path(..., title="message_id", description="The ID of the message to retrieve"),
    handler: AdminHandler = Depends(AdminHandler),
) -> MessageDetails:
    message = await handler.get_message_details(message_id.upper())
    return message
