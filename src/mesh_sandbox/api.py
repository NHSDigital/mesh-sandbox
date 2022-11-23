from typing import cast

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from .common import exclude_none_json_encoder, logger
from .common.constants import Headers
from .dependencies import get_env_config
from .routers import (
    handshake,
    inbox,
    inbox_count,
    lookup,
    outbox,
    simple,
    tracking,
    update,
)

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
async def exception_handler(_request: Request, _exception: Exception):  # pylint: disable=unused-argument
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "An internal error occurred.\n\nPlease contact support."},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exception: HTTPException):  # pylint: disable=unused-argument
    return JSONResponse(status_code=exception.status_code, content=exception.detail)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):

    for err in exc.errors():
        if err["loc"][0] == "header" and cast(str, err["loc"][1]).lower() == Headers.Authorization.lower():
            return Response(status_code=status.HTTP_403_FORBIDDEN)

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=exclude_none_json_encoder({"detail": exc.errors(), "body": exc.body}),
    )


app.include_router(simple.router)


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
