from typing import cast

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError

from .common import logger
from .common.exceptions import MessagingException
from .dependencies import get_env_config
from .routers import (
    admin,
    handshake,
    inbox,
    inbox_count,
    lookup,
    outbox,
    tracking,
    update,
)
from .views.error import get_error_response, get_validation_error_response

app = FastAPI(
    title="MESH Sandbox",
    version="2.0.0",
    description="sandbox for testing mesh",
    contact={"name": "National Service Desk", "email": "ssd.nationalservicedesk@nhs.net"},
    servers=[
        {"url": "https://msg.dev.spine2.ncrs.nhs.uk", "description": "Development"},
        {"url": "https://msg.int.spine2.ncrs.nhs.uk", "description": "Integration"},
        {"url": "https://msg.intspineservices.nhs.uk", "description": "Integration"},
        {"url": "https://msg.dep.spine2.ncrs.nhs.uk", "description": "Deployment"},
        {"url": "https://mesh-sync.national.ncrs.nhs.uk", "description": "Production"},
        {"url": "https://mesh-sync.spineservices.nhs.uk", "description": "Production"},
    ],
    docs_url=None,
    redoc_url=None,
)


@app.on_event("startup")
async def startup():
    config = get_env_config()
    # pylint: disable=logging-fstring-interpolation
    logger.info(f"startup auth_mode: {config.auth_mode} store_mode: {config.store_mode}")


@app.exception_handler(Exception)
async def exception_handler(request: Request, _exception: Exception):  # pylint: disable=unused-argument
    return get_error_response(request, status.HTTP_500_INTERNAL_SERVER_ERROR)


# pylint: disable=unused-argument
@app.exception_handler(MessagingException)
async def send_message_exception_handler(request: Request, exception: MessagingException):
    return get_error_response(
        request,
        exception.status_code,
        exception.detail,
        message_id=exception.message_id,
        headers=cast(dict, exception.headers),
    )


# pylint: disable=unused-argument
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exception: HTTPException):
    return get_error_response(request, exception.status_code, exception.detail, headers=cast(dict, exception.headers))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return get_validation_error_response(request, exc)


app.include_router(admin.router)


app.include_router(
    handshake.router,
    prefix="/messageexchange/{mailbox_id}",
    tags=["Handshake"],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad request"},
        status.HTTP_403_FORBIDDEN: {"description": "Forbidden"},
    },
)

app.include_router(
    inbox.router,
    prefix="/messageexchange/{mailbox_id}/inbox",
    tags=["Inbox"],
    responses={status.HTTP_403_FORBIDDEN: {"description": "Forbidden"}},
)

app.include_router(
    inbox_count.router,
    prefix="/messageexchange/{mailbox_id}/count",
    tags=["Inbox"],
    responses={status.HTTP_403_FORBIDDEN: {"description": "Forbidden"}},
)

app.include_router(
    outbox.router,
    prefix="/messageexchange/{mailbox_id}/outbox",
    tags=["Outbox"],
    responses={status.HTTP_403_FORBIDDEN: {"description": "Forbidden"}},
)

app.include_router(
    tracking.router,
    prefix="/messageexchange/{mailbox_id}/outbox",
    tags=["Tracking"],
    responses={status.HTTP_403_FORBIDDEN: {"description": "Forbidden"}},
)

app.include_router(
    lookup.router,
    prefix="/messageexchange",
    tags=["Lookup"],
    responses={status.HTTP_400_BAD_REQUEST: {"description": "Bad request"}},
)

app.include_router(
    update.router,
    prefix="/messageexchange/{mailbox_id}/update",
    tags=["update"],
    responses={status.HTTP_403_FORBIDDEN: {"description": "Forbidden"}},
)
