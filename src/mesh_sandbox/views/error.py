from typing import Optional, Union, cast

from fastapi import Request, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field  # pylint: disable=no-name-in-module
from starlette.responses import JSONResponse

from ..common import MESH_MEDIA_TYPES, exclude_none_json_encoder
from ..common.constants import Headers
from ..common.exceptions import try_parse_error
from ..dependencies import parse_accept_header


class MeshErrorV1(BaseModel):
    messageID: Optional[str] = Field(description="message_id associated with the error", default=None)
    errorEvent: Optional[str] = Field(description="message error phase", default="")
    errorCode: Optional[str] = Field(description="message error code", default="")
    errorDescription: Optional[str] = Field(description="message error description", default="")

    class Config:
        title = "mesh_error_v1"
        json_schema_extra = {
            "example": {
                "messageID": "20220228174323222_ABCDEF",
                "errorEvent": "SEND",
                "errorCode": "01",
                "errorDescription": "send failed for some reason",
            }
        }


class MeshErrorV2(BaseModel):
    message_id: Optional[str] = Field(description="message id associated with the error", default=None)
    internal_id: Optional[str] = Field(description="internal id associated with the error", default=None)
    detail: list[dict] = Field(description="error detail", default_factory=list)

    class Config:
        title = "mesh_error_v2"
        json_schema_extra = {
            "example": {
                "message_id": "20220228174323222_ABCDEF",
                "internal_id": "20220228174323222_ABCDEF",
                "detail": [{"event": "SEND", "code": "01", "msg": "send failed for some reason"}],
            }
        }


def get_validation_error_response(_request: Request, exc: RequestValidationError) -> Response:
    for err in exc.errors():
        if err["loc"][0] == "header" and cast(str, err["loc"][1]).lower() == Headers.Authorization.lower():
            return Response(status_code=status.HTTP_403_FORBIDDEN)

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=exclude_none_json_encoder({"detail": exc.errors(), "body": exc.body}),
    )


_DEFAULT_ERROR_MESSAGE = "An internal error occurred.\n\nPlease contact support."


def get_error_response(
    request: Request,
    status_code: int,
    detail: Union[str, dict, None] = None,
    message_id: Optional[str] = None,
    headers: Optional[dict] = None,  # type: ignore[assignment]
) -> JSONResponse:
    internal_id = None
    if hasattr(request.state, "internal_id"):
        internal_id = request.state.internal_id

    if not detail:
        return JSONResponse(
            status_code=status_code,
            headers=headers,
            content=exclude_none_json_encoder({"internal_id": internal_id, "message": _DEFAULT_ERROR_MESSAGE}),
        )

    accepts_api_version = parse_accept_header(request.headers.get(Headers.Accept)) or 1

    content = try_parse_error(detail=detail, message_id=message_id)

    if "errorDescription" not in content:
        return JSONResponse(status_code=status_code, headers=headers, content=exclude_none_json_encoder(content))

    v1_error = MeshErrorV1(**content)
    if accepts_api_version < 2:
        return JSONResponse(status_code=status_code, headers=headers, content=exclude_none_json_encoder(v1_error))

    v2_error = MeshErrorV2(
        message_id=v1_error.messageID,
        internal_id=internal_id,
        detail=[{"event": v1_error.errorEvent, "code": v1_error.errorCode, "msg": v1_error.errorDescription}],
    )

    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content=exclude_none_json_encoder(v2_error),
        media_type=MESH_MEDIA_TYPES[2],
    )
