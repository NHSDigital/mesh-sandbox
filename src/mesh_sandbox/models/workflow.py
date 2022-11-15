from dataclasses import dataclass, field


@dataclass
class Workflow:

    workflow_id: str
    senders: list[str] = field(default_factory=list)
    receivers: list[str] = field(default_factory=list)

    def __post_init__(self):

        self.workflow_id = (self.workflow_id or "").strip()

        self.senders = [mailbox for mailbox in ((mb or "").strip().upper() for mb in self.senders) if mailbox]
        self.receivers = [mailbox for mailbox in ((mb or "").strip().upper() for mb in self.receivers) if mailbox]
