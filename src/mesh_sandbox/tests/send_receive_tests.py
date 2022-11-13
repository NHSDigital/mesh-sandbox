from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from ..common import APP_V1_JSON, APP_V2_JSON
from ..common.constants import Headers
from .helpers import generate_auth_token, send_message

_CANNED_MAILBOX1 = "X26ABC1"
_CANNED_MAILBOX2 = "X26ABC2"


@pytest.mark.parametrize("accept", [APP_V1_JSON, APP_V2_JSON])
def test_memory_send_message_with_local_id(app: TestClient, accept: str):

    sender = _CANNED_MAILBOX1
    recipient = _CANNED_MAILBOX2

    res = app.get(
        f"/messageexchange/{recipient}/inbox",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )

    list_inbox_response = res.json()
    assert list_inbox_response["messages"] == []

    local_id = uuid4().hex
    workflow_id = "TEST_MATT_WORKFLOW"

    message_body = f"test{uuid4().hex}".encode()

    resp = send_message(
        app,
        sender_mailbox_id=sender,
        recipient_mailbox_id=recipient,
        workflow_id=workflow_id,
        message_data=message_body,
        extra_headers={Headers.Accept: accept, Headers.Mex_LocalID: local_id},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    result = resp.json()
    message_id = result["messageID"] if accept == APP_V1_JSON else result["message_id"]
    assert message_id

    res = app.head(
        f"/messageexchange/{recipient}/inbox/{message_id}",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )

    assert res.status_code == 200
    assert res.headers[Headers.Mex_From] == sender
    assert res.headers[Headers.Mex_To] == recipient
    assert res.headers[Headers.Mex_LocalID] == local_id
    assert res.headers[Headers.Mex_WorkflowID] == workflow_id

    res = app.get(
        f"/messageexchange/{recipient}/inbox/{message_id}",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )

    assert res.status_code == 200
    assert res.headers[Headers.Mex_From] == sender
    assert res.headers[Headers.Mex_To] == recipient
    assert res.headers[Headers.Mex_LocalID] == local_id
    assert res.headers[Headers.Mex_WorkflowID] == workflow_id

    assert res.content == message_body

    res = app.get(
        f"/messageexchange/{sender}/outbox/tracking?messageID={message_id}",
        headers={Headers.Authorization: generate_auth_token(sender), Headers.Accept: accept},
    )

    assert res.status_code == 200

    res = app.get(
        f"/messageexchange/{sender}/outbox/tracking/{local_id}",
        headers={Headers.Authorization: generate_auth_token(sender)},
    )

    assert res.status_code == 200
