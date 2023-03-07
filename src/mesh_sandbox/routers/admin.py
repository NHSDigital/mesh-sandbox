from fastapi import APIRouter, Depends, Query, status

from ..dependencies import EnvConfig, get_env_config, normalise_mailbox_id_path
from ..handlers.reset import ResetHandler
from .request_logging import RequestLoggingRoute

router = APIRouter(
    route_class=RequestLoggingRoute,
)


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


@router.get(
    "/messageexchange/reset", status_code=status.HTTP_200_OK, include_in_schema=False, response_model_exclude_none=True
)
async def reset(
    clear_disk: str = Query(
        default="true",
        title="Clear disk",
        description="whether to clear the filesystem store if STORE_MODE=file, otherwise ignored",
        example="true",
    ),
    handler: ResetHandler = Depends(ResetHandler),
):
    await handler.reset(clear_disk.lower() == "true")
    return {"message": "all mailboxes reset"}


@router.get(
    "/messageexchange/reset/{mailbox_id}",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    response_model_exclude_none=True,
)
async def reset_mailbox(
    clear_disk: str = Query(
        default="true",
        title="Clear disk",
        description="whether to clear the filesystem store if STORE_MODE=file, otherwise ignored",
        example="true",
    ),
    mailbox_id: str = Depends(normalise_mailbox_id_path),
    handler: ResetHandler = Depends(ResetHandler),
):
    await handler.reset(clear_disk.lower() == "true", mailbox_id)
    return {"message": "mailbox {mailbox_id} reset"}
