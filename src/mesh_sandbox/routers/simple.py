from fastapi import APIRouter, Depends, status

from ..dependencies import EnvConfig, get_env_config
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
