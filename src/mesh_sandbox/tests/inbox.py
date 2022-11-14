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
def test_inbox_count(app: TestClient, accept: str):

    sender = _CANNED_MAILBOX1
    recipient = _CANNED_MAILBOX2

    res = app.get(
        f"/messageexchange/{recipient}/inbox",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )

    list_inbox_response = res.json()
    assert list_inbox_response["messages"] == []

    res = app.get(
        f"/messageexchange/{recipient}/count",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["count"] == 0

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

    res = app.get(
        f"/messageexchange/{recipient}/count",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["count"] == 1


@pytest.mark.parametrize("accept", [APP_V1_JSON, APP_V2_JSON])
def test_paginated_inbox_outbox(app: TestClient, accept: str):
    # pylint: disable=too-many-statements

    sender = _CANNED_MAILBOX1
    recipient = _CANNED_MAILBOX2

    res = app.get(
        f"/messageexchange/{recipient}/inbox",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )

    response = res.json()
    assert response["messages"] == []

    page_size = 10

    message_ids = []
    for _ in range(page_size * 3):

        resp = send_message(
            app,
            sender_mailbox_id=sender,
            recipient_mailbox_id=recipient,
            extra_headers={Headers.Accept: accept},
        )

        assert resp.status_code == status.HTTP_202_ACCEPTED
        result = resp.json()
        message_id = result["messageID"] if accept == APP_V1_JSON else result["message_id"]
        assert message_id
        message_ids.append(message_id)

    # inbox

    res = app.get(
        f"/messageexchange/{recipient}/inbox?max_results={page_size}",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )

    response = res.json()
    messages = response["messages"]
    assert messages == message_ids[:page_size]

    if accept == APP_V1_JSON:

        res = app.get(
            f"/messageexchange/{recipient}/inbox?max_results={page_size}&continue_from={messages[-1]}",
            headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
        )

        response = res.json()
        assert response["messages"] == message_ids[page_size : page_size * 2]
    else:
        next_page = response["links"].get("next")
        assert next_page
        res = app.get(
            next_page,
            headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
        )
        response = res.json()
        assert response["messages"] == message_ids[page_size : page_size * 2]

    # rich inbox

    res = app.get(
        f"/messageexchange/{recipient}/inbox/rich?max_results={page_size}",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )

    assert res.status_code == status.HTTP_200_OK
    response = res.json()
    messages = [res["message_id"] for res in response.get("messages", [])]
    assert messages == message_ids[:page_size]

    next_page = response["links"].get("next")
    assert next_page
    res = app.get(
        next_page,
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )
    response = res.json()
    messages = [res["message_id"] for res in response.get("messages", [])]
    assert messages == message_ids[page_size : page_size * 2]

    # rich outbox

    res = app.get(
        f"/messageexchange/{sender}/outbox/rich?max_results={page_size}",
        headers={Headers.Authorization: generate_auth_token(sender), Headers.Accept: accept},
    )

    message_ids = list(reversed(message_ids))

    assert res.status_code == status.HTTP_200_OK
    response = res.json()
    messages = [res["message_id"] for res in response.get("messages", [])]
    assert messages == message_ids[:page_size]

    next_page = response["links"].get("next")
    assert next_page
    res = app.get(
        next_page,
        headers={Headers.Authorization: generate_auth_token(sender), Headers.Accept: accept},
    )
    response = res.json()
    messages = [res["message_id"] for res in response.get("messages", [])]
    assert messages == message_ids[page_size : page_size * 2]
