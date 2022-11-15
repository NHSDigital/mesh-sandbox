from typing import Any, Optional, Union, cast

from fastapi import APIRouter, Depends, Header, Request, status

from ..common.constants import Headers
from ..dependencies import authorised_mailbox, get_accepts_api_version
from ..handlers.handshake import HandshakeHandler
from ..models.mailbox import Mailbox
from .request_logging import RequestLoggingRoute

router = APIRouter(
    dependencies=[Depends(authorised_mailbox)],
    route_class=RequestLoggingRoute,
)

_HANDSHAKE_SUMMARY = "Validate a mailbox (Handshake)"
_HANDSHAKE_RESPONSES: Optional[dict[Union[int, str], dict[str, Any]]] = {
    status.HTTP_200_OK: {"content": None},
    status.HTTP_403_FORBIDDEN: {"description": "Authentication failed", "content": None},
}


@router.get(
    "",
    summary=_HANDSHAKE_SUMMARY,
    responses=_HANDSHAKE_RESPONSES,
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
    openapi_extra={"spec_order": 110},
)
@router.post(
    "",
    summary=_HANDSHAKE_SUMMARY,
    responses=_HANDSHAKE_RESPONSES,
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
    openapi_extra={"spec_order": 111},
)
async def handshake(  # pylint: disable=too-many-arguments
    request: Request,
    user_agent: str = Header(
        title=Headers.User_Agent, description="User agent string", example="my-client;windows-10;", default=""
    ),
    mex_clientversion: str = Header(
        ...,
        title=Headers.Mex_ClientVersion,
        description="Client version number",
        example="ApiDocs==0.0.1",
    ),
    mex_osname: str = Header(
        ...,
        title=Headers.Mex_OSName,
        description="Operating system name",
        example="Linux",
    ),
    mex_osversion: str = Header(
        ..., title=Headers.Mex_OSVersion, description="Operating system version", example="#44~18.04.2-Ubuntu"
    ),
    mex_javaversion: str = Header(
        title=Headers.Mex_JavaVersion,
        description="Java Version, optional",
        example="openjdk-11u",
        default="",
        include_in_schema=False,
    ),
    mex_osarchitecture: str = Header(
        title=Headers.Mex_OSArchitecture,
        description="OS Architecture, optional",
        example="x86-64",
        default="",
        include_in_schema=False,
    ),
    accepts_api_version: int = Depends(get_accepts_api_version),
    handler: HandshakeHandler = Depends(HandshakeHandler),
):
    return await handler.handshake(
        cast(Mailbox, request.state.authorised_mailbox),
        request,
        user_agent,
        mex_clientversion,
        mex_osname,
        mex_osversion,
        mex_javaversion,
        mex_osarchitecture,
        accepts_api_version,
    )
