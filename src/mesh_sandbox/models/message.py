from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Final, Generator, Optional

from dateutil.relativedelta import relativedelta


class MessageStatus:

    UPLOADING: Final[str] = "uploading"  # still uploading chunks
    ACCEPTED: Final[str] = "accepted"  # finished uploading
    ACKNOWLEDGED: Final[str] = "acknowledged"  # client has acknowledged the message
    UNDELIVERABLE: Final[str] = "undeliverable"  # cannot deliver to recipient (what about multiple recipients?)
    ERROR: Final[str] = "error"  # cannot deliver to recipient (what about multiple recipients?)

    VALID_VALUES: Final[list[str]] = [UPLOADING, ACCEPTED, ACKNOWLEDGED, UNDELIVERABLE, ERROR]


class MessageType:

    REPORT: Final[str] = "REPORT"
    DATA: Final[str] = "DATA"

    VALID_VALUES: Final[list[str]] = [DATA, REPORT]


class MessageDeliveryStatus:
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


@dataclass
class MessageMetadata:

    subject: Optional[str] = field(default=None)
    content_encoding: Optional[str] = field(default=None)
    file_name: Optional[str] = field(default=None)
    local_id: Optional[str] = field(default=None)
    partner_id: Optional[str] = field(default=None)
    checksum: Optional[str] = field(default=None)
    encrypted: Optional[bool] = field(default=None)
    is_compressed: Optional[bool] = field(default=None)
    etag: Optional[str] = field(default=None)
    last_modified: Optional[str] = field(default=None)


@dataclass
class MessageParty:
    """This will be either a sender or a recipient."""

    mailbox_id: str = field(default="")
    mailbox_name: Optional[str] = field(default=None)
    org_code: Optional[str] = field(default=None)
    ods_code: Optional[str] = field(default=None)
    org_name: Optional[str] = field(default=None)
    billing_entity: Optional[str] = field(default=None)

    def __post_init__(self):
        self.mailbox_id = (self.mailbox_id or "").strip().upper()


@dataclass
class MessageEvent:
    status: str
    code: Optional[str] = field(default=None)
    event: Optional[str] = field(default=None)
    description: Optional[str] = field(default=None)
    timestamp: Optional[datetime] = field(default_factory=datetime.utcnow)
    linked_message_id: Optional[str] = field(default=None)


def default_message_expiry_time(relative_to: Optional[datetime] = None) -> datetime:
    relative_to = relative_to or datetime.utcnow()
    return relative_to + relativedelta(days=30)


def default_inbox_expiry_time(relative_to: Optional[datetime] = None) -> datetime:
    relative_to = relative_to or datetime.utcnow()
    return relative_to + relativedelta(days=5)


@dataclass
class Message:  # pylint: disable=too-many-public-methods,too-many-instance-attributes
    """Message definition"""

    # required
    message_id: str
    recipient: MessageParty = field(default_factory=MessageParty)
    sender: MessageParty = field(default_factory=MessageParty)
    events: list[MessageEvent] = field(default_factory=list)
    """ note: events is ordered in reverse, so the most recent event is index 0.
    (this is so we can query the latest event in a conditionexpression in dynamodb)
    """

    metadata: MessageMetadata = field(default_factory=MessageMetadata)

    workflow_id: str = field(default="UNDEFINED")
    message_type: Optional[str] = field(default=None)

    total_chunks: int = field(default=1)
    file_size: int = field(default=0)

    inbox_expiry_timestamp: Optional[datetime] = field(default_factory=default_inbox_expiry_time)
    last_modified: datetime = field(default_factory=datetime.utcnow)
    created_timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def status(self) -> str:
        return self.events[0].status

    @property
    def error_event(self) -> Optional[MessageEvent]:
        return next(self.find_status_events(lambda event: event.status == MessageStatus.ERROR), None)

    @property
    def last_event(self) -> MessageEvent:
        return self.events[0]

    def status_timestamp(self, *statuses: str) -> Optional[datetime]:
        if not statuses:
            return self.last_event.timestamp

        event = self.find_status_event(lambda ev: ev.status in statuses)
        return event.timestamp if event else None

    def find_status_event(self, predicate: Callable[[MessageEvent], bool]) -> Optional[MessageEvent]:
        return next(self.find_status_events(predicate), None)

    def find_status_events(self, predicate: Callable[[MessageEvent], bool]) -> Generator[MessageEvent, None, None]:
        for event in self.events:
            if predicate(event):
                yield event

    def __post_init__(self):

        self.message_id = self.message_id.upper()
        self.events = self.events or [MessageEvent(status=MessageStatus.ACCEPTED, timestamp=self.created_timestamp)]
