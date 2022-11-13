from typing import cast

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from .common import exclude_none_json_encoder
from .common.constants import Headers
from .routers import (
    endpoint_lookup,
    handshake,
    inbox,
    inbox_count,
    outbox,
    simple,
    tracking,
    update,
    workflow_search,
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


@app.exception_handler(Exception)
async def exception_handler(request: Request, exception: Exception):  # pylint: disable=unused-argument
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "An internal error occurred.\n\nPlease contact support."},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exception: HTTPException):  # pylint: disable=unused-argument
    return JSONResponse(status_code=exception.status_code, content=exception.detail)


def global_validation_exception_handler(
    request: Request, exc: RequestValidationError  # pylint: disable=unused-argument
) -> Response:
    for err in exc.errors():
        if err["loc"][0] == "header" and cast(str, err["loc"][1]).lower() == Headers.Authorization.lower():
            return Response(status_code=status.HTTP_403_FORBIDDEN)

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=exclude_none_json_encoder({"detail": exc.errors(), "body": exc.body}),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return global_validation_exception_handler(request, exc)


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
    endpoint_lookup.router,
    prefix="/messageexchange/endpointlookup",
    tags=["Lookup"],
    responses={status.HTTP_400_BAD_REQUEST: {"description": "Bad request"}},
)

app.include_router(
    workflow_search.router,
    prefix="/messageexchange/workflowsearch",
    tags=["Lookup"],
    responses={status.HTTP_400_BAD_REQUEST: {"description": "Bad request"}},
)

app.include_router(
    update.router,
    prefix="/messageexchange/{mailbox_id}/update",
    tags=["update"],
    responses={status.HTTP_403_FORBIDDEN: {"description": "Forbidden"}},
)
