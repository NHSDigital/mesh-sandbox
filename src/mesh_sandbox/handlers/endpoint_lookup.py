from fastapi import Depends, HTTPException, status

from ..common import EnvConfig
from ..dependencies import get_env_config
from ..models.mailbox import Mailbox
from ..views.lookup import endpoint_lookup_response


class EndPointLookupHandler:
    def __init__(self, config: EnvConfig = Depends(get_env_config)):
        self.config = config

    async def get_receiving_mailbox_ids(self, ods_code: str, workflow_id: str, accepts_api_version: int = 1):

        if not ods_code or (ods_code and not ods_code.strip()):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ods code missing")

        if not workflow_id or (workflow_id and not workflow_id.strip()):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workflow id missing")

        mailboxes: list[Mailbox] = []

        return endpoint_lookup_response(mailboxes, accepts_api_version)
