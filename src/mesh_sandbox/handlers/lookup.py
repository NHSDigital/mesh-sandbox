from fastapi import Depends, HTTPException, status

from ..common.messaging import Messaging
from ..dependencies import get_messaging
from ..views.lookup import endpoint_lookup_response, workflow_search_response


class LookupHandler:
    def __init__(self, messaging: Messaging = Depends(get_messaging)):
        self.messaging = messaging

    async def lookup_by_ods_code_and_workflow(self, ods_code: str, workflow_id: str, accepts_api_version: int = 1):
        if not ods_code or (ods_code and not ods_code.strip()):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ods code missing")

        if not workflow_id or (workflow_id and not workflow_id.strip()):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workflow id missing")

        mailboxes = await self.messaging.lookup_by_ods_code_and_workflow_id(ods_code, workflow_id)

        return endpoint_lookup_response(mailboxes, accepts_api_version)

    async def lookup_by_workflow_id(self, workflow_id: str, accepts_api_version: int = 1):
        if not workflow_id or (workflow_id and not workflow_id.strip()):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workflow id missing")

        mailboxes = await self.messaging.lookup_by_workflow_id(workflow_id)

        return workflow_search_response(mailboxes, accepts_api_version)
