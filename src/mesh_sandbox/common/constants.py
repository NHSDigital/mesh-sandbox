from typing import Final

# pylint: disable=invalid-name


class Headers:
    Authorization: Final[str] = "Authorization"
    Last_Modified: Final[str] = "Last-Modified"
    ETag: Final[str] = "ETag"
    Accept: Final[str] = "Accept"
    Accept_Encoding: Final[str] = "Accept-Encoding"
    Content_Type: Final[str] = "Content-Type"
    Content_Encoding: Final[str] = "Content-Encoding"
    Content_Length: Final[str] = "Content-Length"
    User_Agent: Final[str] = "User-Agent"

    Mex_From: Final[str] = "mex-From"
    Mex_To: Final[str] = "mex-To"
    Mex_Chunk_Range: Final[str] = "mex-Chunk-Range"
    Mex_StatusCode: Final[str] = "mex-StatusCode"
    Mex_StatusEvent: Final[str] = "mex-StatusEvent"
    Mex_StatusDescription: Final[str] = "mex-StatusDescription"
    Mex_StatusSuccess: Final[str] = "mex-StatusSuccess"
    Mex_StatusTimestamp: Final[str] = "mex-StatusTimestamp"
    Mex_WorkflowID: Final[str] = "mex-WorkflowID"
    Mex_Content_Compress: Final[str] = "mex-Content-Compress"
    Mex_Content_Encrypted: Final[str] = "mex-Content-Encrypted"
    Mex_Content_Compressed: Final[str] = "mex-Content-Compressed"
    Mex_Content_Checksum: Final[str] = "mex-Content-Checksum"
    Mex_MessageType: Final[str] = "mex-MessageType"
    Mex_MessageID: Final[str] = "mex-MessageID"
    Mex_LocalID: Final[str] = "mex-LocalID"
    Mex_PartnerID: Final[str] = "mex-PartnerID"
    Mex_FileName: Final[str] = "mex-FileName"
    Mex_Subject: Final[str] = "mex-Subject"
    Mex_ClientVersion: Final[str] = "mex-ClientVersion"
    Mex_OSName: Final[str] = "mex-OSName"
    Mex_OSVersion: Final[str] = "mex-OSVersion"
    Mex_OSArchitecture: Final[str] = "mex-OSArchitecture"
    Mex_JavaVersion: Final[str] = "mex-JavaVersion"
    Mex_Version: Final[str] = "mex-Version"
    Mex_LinkedMsgId = "mex-LinkedMsgID"
    Mex_AddressType = "mex-AddressType"


# Error codes
ERROR_INVALID_FROM_ADDRESS: Final = "Invalid From Address"
ERROR_MISSING_TO_ADDRESS: Final = "TO_DTS missing"
ERROR_INVALID_TO_ADDRESS: Final = "Invalid to Address"
ERROR_INVALID_HEADER_CHUNKS = "InvalidHeaderChunks"
UNSUPPORTED_CONTENT_ENCODING = "UnsupportedContentEncoding"
ERROR_INVALID_VERSION: Final = "Invalid Version"
ERROR_MESSAGE_TYPE_INVALID: Final = "Invalid message type"
ERROR_MESSAGE_GONE: Final = "Message already accepted"
ERROR_MESSAGE_DOES_NOT_EXIST: Final = "Message does not exist"
ERROR_MESSAGE_IN_UNEXPECTED_STATUS: Final = "Message in unexpected status"
ERROR_INVALID_EXPIRY_PERIOD: Final = "Invalid expiry period"
ERROR_UNREGISTERED_RECIPIENT: Final = "Unregistered recipient"
ERROR_MISSING_DATA_FILE: Final = "MissingDataFile"
ERROR_INVALID_CONTROL_CHARACTERS: Final = "MalformedControlFile"
ERROR_UNDELIVERED_MESSAGE: Final = "Message not collected by recipient after {0} days"
ERROR_UNDELIVERED_MSG_MAILBOX_DEACTIVATED: Final = "Message was not collected as the mailbox is deactivated"
ERROR_READING_AUTH_HEADER: Final = "Error reading from Authorization header"
ERROR_NOT_REGISTERED_FOR_WORKFLOWID: Final = "Workflow ID not registered for mailbox"
ERROR_TOO_MANY_MAILBOX_MATCHES: Final = "Multiple mailboxes matches"
ERROR_NO_MAILBOX_MATCHES: Final = "No mailbox matched"
ERROR_INACTIVE_MAILBOX: Final = "Request Received from Inactive Mailbox"
ERROR_MAILBOX_TOKEN_MISMATCH: Final = "Mailbox id does not match token"
ERROR_INVALID_AUTH_TOKEN: Final = "Invalid Authentication Token"
ERROR_DUPLICATED_AUTH_TOKEN: Final = "Error Duplicated Authentication Token"
ERROR_CONTENT_ENCODING_CHANGED: Final = "cannot change content encoding"
ERROR_NOT_ENABLED_FOR_ONS_WORKFLOWID: Final = "ONS Civil Registration Workflow ID not enabled via MESH"
ERROR_INVALID_CHECKSUM = "Invalid checksum"
ERROR_INVALID_FILE_FORMAT = "Invalid file format"

ERROR_INVALID_NHSNUMBER = "Invalid NHS Number"
ERROR_NHSNUMBER_NOT_FOUND = "NHS Number not found"
ERROR_NO_DEMOGRAPHICS_MATCH = "NHS Number supplied does not match the demographics"

ERROR_CODE_UNREGISTERED_RECIPIENT: Final = "12"
ERROR_CODE_MAILBOX_NOT_NA_ENABLED: Final = "100"
ERROR_CODE_UNDELIVERED_MESSAGE: Final = "14"
ERROR_CODE_INVALID_CONTROL_CHARACTERS: Final = "06"

# Error Codes are taken from the DTS spec, it is deliberate that 14 is repeated
ErrorCodeMap = {
    ERROR_INVALID_CONTROL_CHARACTERS: ("TRANSFER", ERROR_CODE_INVALID_CONTROL_CHARACTERS, "Malformed control file"),
    ERROR_INVALID_FROM_ADDRESS: ("SEND", "07", "Invalid From Address in the control file"),
    ERROR_MISSING_TO_ADDRESS: ("SEND", "08", "TO_DTS missing"),
    ERROR_INVALID_VERSION: ("SEND", "09", "Invalid version of the control file"),
    ERROR_MESSAGE_TYPE_INVALID: ("SEND", "11", "Invalid Message Type for the transfer"),
    ERROR_INVALID_EXPIRY_PERIOD: ("SEND", "19", "Invalid expiry period"),
    ERROR_UNREGISTERED_RECIPIENT: ("SEND", ERROR_CODE_UNREGISTERED_RECIPIENT, "Unregistered to address"),
    ERROR_UNDELIVERED_MESSAGE: ("SEND", ERROR_CODE_UNDELIVERED_MESSAGE, ERROR_UNDELIVERED_MESSAGE),
    ERROR_UNDELIVERED_MSG_MAILBOX_DEACTIVATED: (
        "SEND",
        ERROR_CODE_UNDELIVERED_MESSAGE,
        ERROR_UNDELIVERED_MSG_MAILBOX_DEACTIVATED,
    ),
    ERROR_MISSING_DATA_FILE: ("COLLECT", "02", "Data file is missing or inaccessible."),
    ERROR_NOT_REGISTERED_FOR_WORKFLOWID: ("SEND", "17", ERROR_NOT_REGISTERED_FOR_WORKFLOWID),
    ERROR_TOO_MANY_MAILBOX_MATCHES: ("SEND", "EPL-150", ERROR_TOO_MANY_MAILBOX_MATCHES),
    ERROR_NO_MAILBOX_MATCHES: ("SEND", "EPL-151", ERROR_NO_MAILBOX_MATCHES),
    ERROR_MESSAGE_GONE: ("SEND", ERROR_MESSAGE_GONE, "Message no longer available for download"),
    ERROR_MESSAGE_DOES_NOT_EXIST: ("RECEIVE", "20", ERROR_MESSAGE_DOES_NOT_EXIST),
    ERROR_NOT_ENABLED_FOR_ONS_WORKFLOWID: (
        "SEND",
        "18",
        "ONS Civil Registration for workflowId {workflowId} is not enabled via MESH",
    ),
    ERROR_INVALID_TO_ADDRESS: (
        "SEND",
        ERROR_CODE_UNREGISTERED_RECIPIENT,
        "Cannot send messages to internal mailbox",
    ),
    ERROR_INVALID_HEADER_CHUNKS: (
        "SEND",
        ERROR_INVALID_HEADER_CHUNKS,
        f"Invalid chunk values sent in {Headers.Mex_Chunk_Range} header",
    ),
    UNSUPPORTED_CONTENT_ENCODING: (
        "SEND",
        UNSUPPORTED_CONTENT_ENCODING,
        "Unsupported content encoding",
    ),
    ERROR_INVALID_CHECKSUM: (
        "SEND",
        ERROR_INVALID_CHECKSUM,
        "Invalid checksum",
    ),
    ERROR_INVALID_FILE_FORMAT: (
        "SEND",
        ERROR_INVALID_FILE_FORMAT,
        "File Level Error (file not formed correctly)",
    ),
}
