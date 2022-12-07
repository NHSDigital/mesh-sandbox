import os.path
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

    assert res.status_code == status.HTTP_200_OK
    assert res.headers[Headers.Mex_From] == sender
    assert res.headers[Headers.Mex_To] == recipient
    assert res.headers[Headers.Mex_LocalID] == local_id
    assert res.headers[Headers.Mex_WorkflowID] == workflow_id

    res = app.get(
        f"/messageexchange/{recipient}/inbox/{message_id}",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )

    assert res.status_code == status.HTTP_200_OK
    assert res.headers[Headers.Mex_From] == sender
    assert res.headers[Headers.Mex_To] == recipient
    assert res.headers[Headers.Mex_LocalID] == local_id
    assert res.headers[Headers.Mex_WorkflowID] == workflow_id

    assert res.content == message_body

    res = app.get(
        f"/messageexchange/{sender}/outbox/tracking?messageID={message_id}",
        headers={Headers.Authorization: generate_auth_token(sender), Headers.Accept: accept},
    )

    assert res.status_code == status.HTTP_200_OK
    expected = MessageStatus.ACCEPTED.title() if accept == APP_V1_JSON else MessageStatus.ACCEPTED
    assert res.json()["status"] == expected

    res = app.get(
        f"/messageexchange/{sender}/outbox/tracking/{local_id}",
        headers={Headers.Authorization: generate_auth_token(sender)},
    )

    assert res.status_code == status.HTTP_200_OK

    assert res.json()["status"] == MessageStatus.ACCEPTED.title()

    res = app.get(
        f"/messageexchange/{recipient}/inbox?workflow_filter={workflow_id}",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )

    list_inbox_response = res.json()
    assert list_inbox_response["messages"] == [message_id]

    res = app.put(
        f"/messageexchange/{recipient}/inbox/{message_id}/status/acknowledged",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )

    assert res.status_code == status.HTTP_200_OK

    if accept == APP_V1_JSON:
        assert res.json()["messageId"] == message_id
    else:
        assert res.text == ""

    res = app.get(
        f"/messageexchange/{recipient}/inbox",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )

    list_inbox_response = res.json()
    assert list_inbox_response["messages"] == []

    res = app.get(
        f"/messageexchange/{sender}/outbox/tracking?messageID={message_id}",
        headers={Headers.Authorization: generate_auth_token(sender), Headers.Accept: accept},
    )
    assert res.status_code == status.HTTP_200_OK
    expected = MessageStatus.ACKNOWLEDGED.title() if accept == APP_V1_JSON else MessageStatus.ACKNOWLEDGED
    assert res.json()["status"] == expected


@pytest.mark.parametrize("accept", [APP_V1_JSON, APP_V2_JSON])
def test_file_send_message_with_local_id(app: TestClient, accept: str, tmp_path: str):

    sender = _CANNED_MAILBOX1
    recipient = _CANNED_MAILBOX2

    with temp_env_vars(STORE_MODE="file", FILE_STORE_DIR=tmp_path):

        res = app.get(
            f"/messageexchange/{recipient}/inbox",
            headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
        )

        list_inbox_response = res.json()
        assert list_inbox_response["messages"] == []

        workflow_id = "TEST_MATT_WORKFLOW"

        message_body = f"test{uuid4().hex}".encode()

        resp = send_message(
            app,
            sender_mailbox_id=sender,
            recipient_mailbox_id=recipient,
            workflow_id=workflow_id,
            message_data=message_body,
            extra_headers={Headers.Accept: accept},
        )

        assert resp.status_code == status.HTTP_202_ACCEPTED
        result = resp.json()
        message_id = result["messageID"] if accept == APP_V1_JSON else result["message_id"]
        assert message_id

        res = app.head(
            f"/messageexchange/{recipient}/inbox/{message_id}",
            headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
        )

        assert res.status_code == status.HTTP_200_OK
        assert res.headers[Headers.Mex_From] == sender
        assert res.headers[Headers.Mex_To] == recipient
        assert res.headers[Headers.Mex_WorkflowID] == workflow_id

        res = app.get(
            f"/messageexchange/{recipient}/inbox/{message_id}",
            headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
        )

        assert res.status_code == status.HTTP_200_OK
        assert res.headers[Headers.Mex_From] == sender
        assert res.headers[Headers.Mex_To] == recipient
        assert res.headers[Headers.Mex_WorkflowID] == workflow_id

        assert res.content == message_body

        message_path = os.path.join(tmp_path, f"{recipient}/in/{message_id}/1")
        assert os.path.exists(message_path)

        with open(message_path, "rb") as f:
            assert f.read() == message_body


@pytest.mark.parametrize("accept", [APP_V1_JSON, APP_V2_JSON])
def test_memory_send_chunked_message(app: TestClient, accept: str):

    sender = _CANNED_MAILBOX1
    recipient = _CANNED_MAILBOX2

    res = app.get(
        f"/messageexchange/{recipient}/inbox",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )

    list_inbox_response = res.json()
    assert list_inbox_response["messages"] == []

    chunk_1 = f"test{uuid4().hex}".encode()
    chunk_2 = f"test{uuid4().hex}".encode()

    workflow_id = "TEST_WORKFLOW"

    resp = send_message(
        app,
        sender_mailbox_id=sender,
        recipient_mailbox_id=recipient,
        workflow_id=workflow_id,
        message_data=chunk_1,
        extra_headers={Headers.Accept: accept, Headers.Mex_Chunk_Range: "1:2"},
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    result = resp.json()
    message_id = result["messageID"] if accept == APP_V1_JSON else result["message_id"]
    assert message_id

    res = app.get(
        f"/messageexchange/{sender}/outbox/tracking?messageID={message_id}",
        headers={Headers.Authorization: generate_auth_token(sender), Headers.Accept: accept},
    )

    assert res.status_code == status.HTTP_200_OK
    expected = MessageStatus.UPLOADING.title() if accept == APP_V1_JSON else MessageStatus.UPLOADING
    assert res.json()["status"] == expected

    res = app.head(
        f"/messageexchange/{recipient}/inbox/{message_id}",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )

    assert res.status_code == status.HTTP_410_GONE

    res = app.post(
        f"/messageexchange/{sender}/outbox/{message_id}/2",
        headers={
            Headers.Authorization: generate_auth_token(sender),
            Headers.Accept: accept,
            Headers.Mex_Chunk_Range: "2:2",
        },
        data=chunk_2,
    )
    assert res.status_code == status.HTTP_202_ACCEPTED, res.text

    res = app.head(
        f"/messageexchange/{recipient}/inbox/{message_id}",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )

    assert res.status_code == status.HTTP_200_OK
    assert res.headers[Headers.Mex_From] == sender
    assert res.headers[Headers.Mex_To] == recipient
    assert res.headers[Headers.Mex_WorkflowID] == workflow_id

    res = app.get(
        f"/messageexchange/{recipient}/inbox/{message_id}",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )

    assert res.status_code == status.HTTP_206_PARTIAL_CONTENT
    assert res.headers[Headers.Mex_From] == sender
    assert res.headers[Headers.Mex_To] == recipient
    assert res.headers[Headers.Mex_WorkflowID] == workflow_id

    assert res.content == chunk_1

    res = app.get(
        f"/messageexchange/{recipient}/inbox/{message_id}/2",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )

    assert res.status_code == status.HTTP_200_OK
    assert res.content == chunk_2

    res = app.get(
        f"/messageexchange/{sender}/outbox/rich",
        headers={Headers.Authorization: generate_auth_token(sender), Headers.Accept: accept},
    )

    assert res.status_code == status.HTTP_200_OK
    messages = res.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["message_id"] == message_id
    assert messages[0]["status"] == MessageStatus.ACCEPTED

    res = app.put(
        f"/messageexchange/{recipient}/inbox/{message_id}/status/acknowledged",
        headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
    )

    assert res.status_code == status.HTTP_200_OK

    res = app.get(
        f"/messageexchange/{sender}/outbox/rich",
        headers={Headers.Authorization: generate_auth_token(sender), Headers.Accept: accept},
    )

    assert res.status_code == status.HTTP_200_OK
    messages = res.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["message_id"] == message_id
    assert messages[0]["status"] == MessageStatus.ACKNOWLEDGED


@pytest.mark.parametrize("accept", [APP_V1_JSON, APP_V2_JSON])
def test_file_send_chunked_message(app: TestClient, accept: str, tmp_path: str):  # pylint: disable=too-many-statements

    sender = _CANNED_MAILBOX1
    recipient = _CANNED_MAILBOX2

    with temp_env_vars(STORE_MODE="file", FILE_STORE_DIR=tmp_path):

        res = app.get(
            f"/messageexchange/{recipient}/inbox",
            headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
        )

        list_inbox_response = res.json()
        assert list_inbox_response["messages"] == []

        chunk_1 = f"test{uuid4().hex}".encode()
        chunk_2 = f"test{uuid4().hex}".encode()

        workflow_id = "TEST_WORKFLOW"

        resp = send_message(
            app,
            sender_mailbox_id=sender,
            recipient_mailbox_id=recipient,
            workflow_id=workflow_id,
            message_data=chunk_1,
            extra_headers={Headers.Accept: accept, Headers.Mex_Chunk_Range: "1:2"},
        )

        assert resp.status_code == status.HTTP_202_ACCEPTED
        result = resp.json()
        message_id = result["messageID"] if accept == APP_V1_JSON else result["message_id"]
        assert message_id

        res = app.get(
            f"/messageexchange/{sender}/outbox/tracking?messageID={message_id}",
            headers={Headers.Authorization: generate_auth_token(sender), Headers.Accept: accept},
        )

        assert res.status_code == status.HTTP_200_OK
        expected = MessageStatus.UPLOADING.title() if accept == APP_V1_JSON else MessageStatus.UPLOADING
        assert res.json()["status"] == expected

        res = app.head(
            f"/messageexchange/{recipient}/inbox/{message_id}",
            headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
        )

        assert res.status_code == status.HTTP_410_GONE

        res = app.post(
            f"/messageexchange/{sender}/outbox/{message_id}/2",
            headers={
                Headers.Authorization: generate_auth_token(sender),
                Headers.Accept: accept,
                Headers.Mex_Chunk_Range: "2:2",
            },
            data=chunk_2,
        )
        assert res.status_code == status.HTTP_202_ACCEPTED, res.text

        res = app.head(
            f"/messageexchange/{recipient}/inbox/{message_id}",
            headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
        )

        assert res.status_code == status.HTTP_200_OK
        assert res.headers[Headers.Mex_From] == sender
        assert res.headers[Headers.Mex_To] == recipient
        assert res.headers[Headers.Mex_WorkflowID] == workflow_id

        res = app.get(
            f"/messageexchange/{recipient}/inbox/{message_id}",
            headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
        )

        assert res.status_code == status.HTTP_206_PARTIAL_CONTENT
        assert res.headers[Headers.Mex_From] == sender
        assert res.headers[Headers.Mex_To] == recipient
        assert res.headers[Headers.Mex_WorkflowID] == workflow_id

        assert res.content == chunk_1

        res = app.get(
            f"/messageexchange/{recipient}/inbox/{message_id}/2",
            headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
        )

        assert res.status_code == status.HTTP_200_OK
        assert res.content == chunk_2

        res = app.get(
            f"/messageexchange/{sender}/outbox/rich",
            headers={Headers.Authorization: generate_auth_token(sender), Headers.Accept: accept},
        )

        assert res.status_code == status.HTTP_200_OK
        messages = res.json()["messages"]
        assert len(messages) == 1
        assert messages[0]["message_id"] == message_id
        assert messages[0]["status"] == MessageStatus.ACCEPTED

        res = app.put(
            f"/messageexchange/{recipient}/inbox/{message_id}/status/acknowledged",
            headers={Headers.Authorization: generate_auth_token(recipient), Headers.Accept: accept},
        )

        assert res.status_code == status.HTTP_200_OK

        res = app.get(
            f"/messageexchange/{sender}/outbox/rich",
            headers={Headers.Authorization: generate_auth_token(sender), Headers.Accept: accept},
        )

        assert res.status_code == status.HTTP_200_OK
        messages = res.json()["messages"]
        assert len(messages) == 1
        assert messages[0]["message_id"] == message_id
        assert messages[0]["status"] == MessageStatus.ACKNOWLEDGED


@pytest.mark.parametrize(
    "value",
    [
        "Y",
        "y",
        "YES",
        "yes",
        "N",
        "n",
        "NO",
        "no",
        "1",
        "0",
        "TRUE",
        "true",
        "FALSE",
        "false",
        "T",
        "F",
        "ON",
        "on",
        "OFF",
        "off",
        ".#!,",
        "N/A",
        "n/a",
    ],
)
def test_mex_content_compress_validation(app: TestClient, value: str):

    sender = _CANNED_MAILBOX1
    recipient = _CANNED_MAILBOX2

    response = send_message(app, sender, recipient, extra_headers={Headers.Mex_Content_Compress: value})

    assert response.status_code == status.HTTP_202_ACCEPTED


@pytest.mark.parametrize(
    "value",
    [
        "Y",
        "y",
        "YES",
        "yes",
        "N",
        "n",
        "NO",
        "no",
        "1",
        "0",
        "TRUE",
        "true",
        "FALSE",
        "false",
        "T",
        "F",
        "ON",
        "on",
        "OFF",
        "off",
        ".#!,",
        "N/A",
        "n/a",
    ],
)
def test_mex_content_encrypted_validation(app: TestClient, value: str):

    sender = _CANNED_MAILBOX1
    recipient = _CANNED_MAILBOX2

    response = send_message(app, sender, recipient, extra_headers={Headers.Mex_Content_Encrypted: value})

    assert response.status_code == status.HTTP_202_ACCEPTED


@pytest.mark.parametrize(
    "value",
    [
        "Y",
        "y",
        "YES",
        "yes",
        "N",
        "n",
        "NO",
        "no",
        "1",
        "0",
        "TRUE",
        "true",
        "FALSE",
        "false",
        "T",
        "F",
        "ON",
        "on",
        "OFF",
        "off",
        ".#!,",
        "N/A",
        "n/a",
    ],
)
def test_mex_content_compressed_validation(app: TestClient, value: str):

    sender = _CANNED_MAILBOX1
    recipient = _CANNED_MAILBOX2

    response = send_message(app, sender, recipient, extra_headers={Headers.Mex_Content_Compressed: value})
    assert response.status_code == status.HTTP_202_ACCEPTED


@pytest.mark.parametrize(
    "mex_content_checksum, expected_response_status",
    [
        ("", status.HTTP_202_ACCEPTED),
        ("b10a8db164e0754105b7a99be72e3fe5", status.HTTP_202_ACCEPTED),
        ("sha256:b10a8db164e0754105b7a99be72e3fe5", status.HTTP_202_ACCEPTED),
        ("sha256: b10a8db164e0754105b7a99be72e3fe5", status.HTTP_202_ACCEPTED),
        ("sha256 - b10a8db164e0754105b7a99be72e3fe5", status.HTTP_202_ACCEPTED),
        ("sha256/b10a8db164e0754105b7a99be72e3fe5", status.HTTP_202_ACCEPTED),
        ("`#!@+&=*,|~;._", status.HTTP_400_BAD_REQUEST),
    ],
)
def test_mex_content_checksum_validation(app: TestClient, mex_content_checksum: str, expected_response_status: int):

    sender = _CANNED_MAILBOX1
    recipient = _CANNED_MAILBOX2

    response = send_message(app, sender, recipient, extra_headers={Headers.Mex_Content_Checksum: mex_content_checksum})

    assert response.status_code == expected_response_status


def test_mex_local_id_validation(app: TestClient):

    sender = _CANNED_MAILBOX1
    recipient = _CANNED_MAILBOX2

    response = send_message(
        app, sender, recipient, extra_headers={Headers.Mex_LocalID: "test#TEST", Headers.Mex_WorkflowID: "test TEST"}
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
