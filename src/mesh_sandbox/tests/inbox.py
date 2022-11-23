from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from ..common import APP_V1_JSON, APP_V2_JSON
from ..common.constants import Headers
from ..models.message import MessageStatus
from .helpers import generate_auth_token, send_message, temp_env_vars

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


def test_receive_canned_chunked_message(app: TestClient):

    with temp_env_vars(STORE_MODE="canned"):

        recipient = _CANNED_MAILBOX2

        res = app.get(
            f"/messageexchange/{recipient}/inbox",
            headers={Headers.Authorization: generate_auth_token(recipient)},
        )

        assert res.status_code == status.HTTP_200_OK
        result = res.json()
        message_ids = result["messages"]
        message_id = "CHUNKED_MESSAGE_GZ"
        assert message_id in message_ids

        res = app.get(
            f"/messageexchange/{recipient}/inbox/{message_id}",
            headers={Headers.Authorization: generate_auth_token(recipient)},
        )
        assert res.status_code == status.HTTP_206_PARTIAL_CONTENT
        message = res.text

        res = app.get(
            f"/messageexchange/{recipient}/inbox/{message_id}/2",
            headers={Headers.Authorization: generate_auth_token(recipient)},
        )
        assert res.status_code == status.HTTP_200_OK
        message += res.text

        assert message.startswith("Lorem ipsum")
        assert message.endswith("lorem.")


def test_receive_canned_simple_message(app: TestClient):

    with temp_env_vars(STORE_MODE="canned"):

        recipient = _CANNED_MAILBOX1

        res = app.get(
            f"/messageexchange/{recipient}/inbox",
            headers={Headers.Authorization: generate_auth_token(recipient)},
        )

        assert res.status_code == status.HTTP_200_OK
        result = res.json()
        message_ids = result["messages"]
        message_id = "SIMPLE_MESSAGE"
        assert message_id in message_ids

        res = app.get(
            f"/messageexchange/{recipient}/inbox/{message_id}",
            headers={Headers.Authorization: generate_auth_token(recipient)},
        )
        assert res.status_code == status.HTTP_200_OK
        message = res.text

        assert message.startswith("Lorem ipsum")
        assert message.endswith("lorem.")


@pytest.mark.parametrize("accept", [APP_V1_JSON, APP_V2_JSON])
def test_receive_canned_undelivered_message(app: TestClient, accept: str):

    recipient = _CANNED_MAILBOX1
    sender = _CANNED_MAILBOX2

    with temp_env_vars(STORE_MODE="canned"):

        res = app.get(
            f"/messageexchange/{recipient}/inbox",
            headers={Headers.Accept: accept, Headers.Authorization: generate_auth_token(recipient)},
        )

        assert res.status_code == status.HTTP_200_OK
        result = res.json()
        message_ids = result["messages"]
        message_id = "UNDELIVERED_MESSAGE"
        assert message_id not in message_ids

        res = app.get(
            f"/messageexchange/{sender}/outbox/tracking?messageID={message_id}",
            headers={Headers.Accept: accept, Headers.Authorization: generate_auth_token(sender)},
        )

        assert res.status_code == status.HTTP_200_OK
        result = res.json()
        assert result["status"] == MessageStatus.UNDELIVERABLE
