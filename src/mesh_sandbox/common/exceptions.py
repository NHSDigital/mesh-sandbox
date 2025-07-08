from typing import Any, Optional, Union

from mesh_sandbox.views.admin import CreateReportRequest

from ..models.message import MessageEvent, MessageMetadata, MessageStatus
from . import constants


class MessagingException(Exception):
    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Optional[dict[str, Any]] = None,
        message_id: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.status_code = status_code
        self.detail = detail
        self.headers = headers
        self.message_id = message_id


def parse_error(
    detail: Optional[str] = None, message_id: Optional[str] = None, format_params: Optional[tuple] = None
) -> dict:
    if detail is None:
        raise ValueError("error_code or error_description must be supplied")

    error_event, error_code, error_message = constants.ErrorCodeMap.get(detail)  # type: ignore[misc]
    err_response = {
        "errorEvent": error_event,
        "errorCode": error_code,
        "errorDescription": error_message.format(*format_params) if format_params else error_message,
    }
    if message_id:
        err_response["messageID"] = message_id
    return err_response


def try_parse_error(detail: Union[str, dict, None] = None, message_id: Optional[str] = None) -> dict:
    if isinstance(detail, str):
        if detail in constants.ErrorCodeMap:
            return parse_error(detail=detail, message_id=message_id)
        return {"errorDescription": detail}

    if isinstance(detail, dict):
        return detail
    return {"errorDescription": str(detail)}


def get_ndr_error() -> dict:
    expiry_period = constants.MESSAGE_IN_INBOX_EXPIRY_IN_DAYS
    error_description = parse_error(
        detail=constants.ERROR_UNDELIVERED_MESSAGE,
        format_params=(expiry_period,),
    )

    return error_description


def create_ndr_event(request: CreateReportRequest) -> MessageEvent:
    error_description = get_ndr_error()

    error_code = error_description.get("errorCode")
    error_event = error_description.get("errorEvent")
    error_message = error_description.get("errorDescription")

    return MessageEvent(
        status=MessageStatus.ERROR,
        code=error_code,
        event=error_event,
        description=error_message,
        linked_message_id=request.linked_message_id,
    )


def create_ndr_metadata(request: CreateReportRequest) -> MessageMetadata:
    subject = "NDR" if not request.subject else f"NDR: {request.subject}"

    return MessageMetadata(
        subject=subject,
        local_id=request.local_id,
    )
