from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Mailbox:

    mailbox_id: str
    mailbox_name: str
    billing_entity: Optional[str] = field(default=None)
    ods_code: str = field(default="")
    org_code: str = field(default="")
    org_name: str = field(default="")
    password: str = field(default="")

    _last_accessed: Optional[datetime] = None
    _inbox_count: Optional[int] = None

    @property
    def last_accessed(self) -> Optional[datetime]:
        return self._last_accessed

    @last_accessed.setter
    def last_accessed(self, last_accessed: Optional[datetime]):
        self._last_accessed = last_accessed

    @property
    def inbox_count(self) -> Optional[int]:
        return self._inbox_count

    @inbox_count.setter
    def inbox_count(self, inbox_count: Optional[int]):
        self._inbox_count = inbox_count

    def __post_init__(self):

        self.mailbox_id = self.mailbox_id.upper()
