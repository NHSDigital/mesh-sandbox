from typing import Optional

from fastapi import Depends, HTTPException, status

from ..common.messaging import Messaging
from ..dependencies import get_messaging
from ..models.mailbox import Mailbox
from ..views.admin import MailboxDetails


class MailboxInfoHandler:
    def __init__(self, messaging: Messaging = Depends(get_messaging)):
        self.messaging = messaging

    async def get_mailbox_details(self, mailbox_id: str) -> MailboxDetails:
        mailbox: Optional[Mailbox] = await self.messaging.get_mailbox(mailbox_id)
        if not mailbox:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        return MailboxDetails.from_mailbox(mailbox)
