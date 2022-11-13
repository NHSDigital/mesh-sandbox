from fastapi import Depends, HTTPException, status

from ..common import EnvConfig
from ..dependencies import get_env_config
from ..models.mailbox import Mailbox
from ..views.lookup import workflow_search_response


class WorkflowSearchHandler:
    def __init__(
        self,
        config: EnvConfig = Depends(get_env_config),
    ):
        self.config = config

    async def get_receiving_mailbox_ids(self, workflow_id: str, accepts_api_version: int = 1):

        if not workflow_id or (workflow_id and not workflow_id.strip()):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workflow id missing")

        mailboxes: list[Mailbox] = []

        return workflow_search_response(mailboxes, accepts_api_version)
