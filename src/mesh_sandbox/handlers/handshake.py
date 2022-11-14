# pylint: disable=unused-argument

from fastapi import Request, Response

from ..models.mailbox import Mailbox


class HandshakeHandler:

    # pylint: disable=too-many-arguments
    async def handshake(
        self,
        mailbox: Mailbox,
        request: Request,
        user_agent: str,
        mex_clientversion: str,
        mex_osname: str,
        mex_osversion: str,
        mex_javaversion: str,
        mex_osarchitecture: str,
        accepts_api_version: int = 1,
    ):

        if accepts_api_version < 2:
            return {"mailboxId": mailbox.mailbox_id}

        return Response()
