import re
import string
from typing import Any, NamedTuple, Optional

from fastapi import Header, HTTPException, status

from ..models.message import Message
from . import strtobool
from .constants import Headers


def ensure_text(text: str, encoding="utf-8", errors="strict"):
    if isinstance(text, str):
        return text

    if isinstance(text, bytes):
        return text.decode(encoding, errors)

    raise TypeError(f"not expecting type '{type(text)}'")


_INVALID_CONTROL_CHAR_REGEX = re.compile(r".*[\x00-\x1f].*")


def contains_control_chars(value: str):
    return _INVALID_CONTROL_CHAR_REGEX.match(ensure_text(value))


class MexHeaders(NamedTuple):
    mex_to: str
    mex_workflow_id: str
    mex_chunk_range: Optional[str]
    mex_subject: Optional[str]
    mex_localid: Optional[str]
    mex_partnerid: Optional[str]
    mex_filename: Optional[str]
    mex_content_encrypted: bool
    mex_content_compressed: bool
    mex_content_checksum: Optional[str]
    mex_content_type: Optional[str]

    def update(self, **kwargs):
        if not kwargs:
            return self
        updated = self._asdict()  # pylint: disable=no-member
        updated.update(kwargs)
        return MexHeaders(*[updated[f] for f in self._fields])  # pylint: disable=no-member

    @classmethod
    def from_message(cls, message: Message, chunk_range: Optional[str], **kwargs):
        create: dict[str, Any] = {
            "mex_to": message.recipient.mailbox_id,
            "mex_workflow_id": message.workflow_id,
            "mex_chunk_range": chunk_range,
            "mex_subject": message.metadata.subject,
            "mex_localid": message.metadata.local_id,
            "mex_partnerid": message.metadata.partner_id,
            "mex_filename": message.metadata.file_name,
            "mex_content_encrypted": message.metadata.encrypted,
            "mex_content_compressed": message.metadata.compressed,
            "mex_content_checksum": message.metadata.checksum,
            "mex_content_type": message.metadata.content_type,
        }

        if kwargs:
            create.update(kwargs)
        return MexHeaders(*[create[f] for f in cls._fields])  # pylint: disable=no-member


def validate_content_checksum(content_checksum: Optional[str]):
    if not content_checksum:
        return

    content_checksum = content_checksum.strip()
    special_chars = ":-/"
    chars_allowed = string.ascii_letters + string.digits + string.whitespace + special_chars
    if all(char in chars_allowed for char in content_checksum):
        return

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid checksum")


_URL_REGEX = re.compile("^https?://", re.IGNORECASE)


def _validate_headers(mex_headers: MexHeaders):
    bad_fields = []
    for key, value in mex_headers._asdict().items():
        if type(value) not in (str, bytes):
            continue

        if not contains_control_chars(ensure_text(value)):
            continue
        bad_fields.append(key)

    if mex_headers.mex_to and _URL_REGEX.match(mex_headers.mex_to):
        bad_fields.append(Headers.Mex_To)

    if mex_headers.mex_workflow_id and _URL_REGEX.match(mex_headers.mex_workflow_id):
        bad_fields.append(Headers.Mex_WorkflowID)

    if mex_headers.mex_content_checksum and _URL_REGEX.match(mex_headers.mex_content_checksum):
        bad_fields.append(Headers.Mex_Content_Checksum)

    if bad_fields:
        err = {
            "errorEvent": "TRANSFER",
            "errorCode": "06",
            "errorDescription": "MalformedControlFile",
            "fields": bad_fields,
        }
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    validate_content_checksum(mex_headers.mex_content_checksum)


# pylint: disable=too-many-arguments
def send_message_mex_headers(
    mex_to: str = Header(
        ..., title=Headers.Mex_To, description="Recipient mailbox ID", example="MAILBOX01", max_length=100
    ),
    mex_workflowid: str = Header(
        ...,
        title=Headers.Mex_WorkflowID,
        description="Identifies the type of message being sent e.g. Pathology, GP Capitation.",
        max_length=300,
    ),
    mex_chunk_range: str = Header(title=Headers.Mex_Chunk_Range, default="", example="1:2", max_length=20),
    mex_subject: str = Header(title=Headers.Mex_Subject, default="", max_length=500),
    mex_localid: str = Header(title=Headers.Mex_LocalID, default="", max_length=300),
    mex_partnerid: str = Header(title=Headers.Mex_PartnerID, default="", max_length=500),
    mex_filename: str = Header(title=Headers.Mex_FileName, default="", max_length=300),
    mex_content_encrypted: str = Header(
        title=Headers.Mex_Content_Encrypted,
        default="",
        description="Flag indicating that the original message is encrypted, "
        "this has no affect on the content, but will be flowed to the recipient",
        example="Y",
        include_in_schema=False,
        max_length=20,
    ),
    mex_content_compressed: str = Header(
        title=Headers.Mex_Content_Compressed,
        default="",
        description="""Flag indicating that the original message has been compressed by the mesh client""",
        example="Y",
        include_in_schema=False,
        max_length=20,
    ),
    mex_content_checksum: str = Header(
        title=Headers.Mex_Content_Checksum,
        default="",
        description="Checksum of the original message contents, as provided by the message sender",
        example="b10a8db164e0754105b7a99be72e3fe5",
        max_length=100,
    ),
    mex_content_type: str = Header(
        title=Headers.Mex_Content_Type,
        default="",
        description=(
            "Content Type of the overall message, overrides Content-Type and "
            "is passed through to recipient, for chunked messages Content-Type will "
            "always be application/octet-stream but Mex-Content-Type will be preserved"
        ),
        example="application/json",
        max_length=100,
    ),
) -> MexHeaders:
    mex_headers = MexHeaders(
        mex_to=(mex_to or "").upper().strip(),
        mex_workflow_id=(mex_workflowid or "").strip(),
        mex_chunk_range=(mex_chunk_range or "").strip(),
        mex_subject=mex_subject,
        mex_localid=mex_localid,
        mex_partnerid=mex_partnerid,
        mex_filename=mex_filename,
        mex_content_encrypted=strtobool(mex_content_encrypted) or False,
        mex_content_compressed=strtobool(mex_content_compressed) or False,
        mex_content_checksum=mex_content_checksum,
        mex_content_type=mex_content_type,
    )
    _validate_headers(mex_headers=mex_headers)
    return mex_headers
