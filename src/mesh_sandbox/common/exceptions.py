from typing import Any, Optional, Union

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
