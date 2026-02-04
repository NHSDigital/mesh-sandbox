from uuid import uuid4

import httpx
import pytest
from fastapi import status
from mesh_client import MeshClient
from requests.models import HTTPError

from mesh_sandbox.tests.docker_tests import (
    _CANNED_MAILBOX1,
    _CANNED_MAILBOX2,
    _PASSWORD,
    _SHARED_KEY,
)


def _mesh_client_send_message(
    base_uri: str,
    sender_mailbox_id: str,
    recipient_mailbox_id: str,
    workflow_id: str,
    payload: bytes,
):
    with MeshClient(
        url=base_uri, mailbox=sender_mailbox_id, password=_PASSWORD, shared_key=_SHARED_KEY, max_chunk_size=100
    ) as sender:
        message_id = sender.send_message(recipient_mailbox_id, payload, workflow_id=workflow_id)
        assert message_id
        return message_id


def _mesh_client_get_inbox_count(base_uri: str, recipient_mailbox_id: str):
    with MeshClient(
        url=base_uri, mailbox=recipient_mailbox_id, password=_PASSWORD, shared_key=_SHARED_KEY
    ) as recipient:
        message_ids = recipient.list_messages()
        return len(message_ids)


def _mesh_client_track_message_by_message_id(base_uri: str, sender_mailbox_id: str, message_id: str):
    with MeshClient(
        url=base_uri, mailbox=sender_mailbox_id, password=_PASSWORD, shared_key=_SHARED_KEY, max_chunk_size=100
    ) as sender:
        tracking = sender.track_message(message_id)
        assert tracking
        return tracking


def test_app_health(base_uri: str):
    with httpx.Client(base_url=base_uri) as client:
        res = client.get("/health")
        assert res.status_code == status.HTTP_200_OK


def test_handshake(base_uri: str):
    with MeshClient(url=base_uri, mailbox=_CANNED_MAILBOX1, password=_PASSWORD, shared_key=_SHARED_KEY) as client:
        res = client.handshake()
        assert res == b"hello"


def test_handshake_bad_password(base_uri: str):
    with MeshClient(url=base_uri, mailbox=_CANNED_MAILBOX1, password="BAD", shared_key=_SHARED_KEY) as client:
        with pytest.raises(HTTPError) as err:
            client.handshake()
        assert err.value.response is not None
        assert err.value.response.status_code == status.HTTP_403_FORBIDDEN


def test_send_receive_chunked_message(base_uri: str):
    workflow_id = uuid4().hex
    sent_payload = b"a" * 1000
    message_id = _mesh_client_send_message(base_uri, _CANNED_MAILBOX1, _CANNED_MAILBOX2, workflow_id, sent_payload)
    assert _mesh_client_get_inbox_count(base_uri, _CANNED_MAILBOX2) == 1

    with MeshClient(url=base_uri, mailbox=_CANNED_MAILBOX2, password=_PASSWORD, shared_key=_SHARED_KEY) as recipient:
        message_ids = recipient.list_messages()
        assert message_ids == [message_id]
        message = recipient.retrieve_message(message_id)
        assert message.workflow_id == workflow_id  # pylint: disable=no-member
        received_payload = message.read()
        assert received_payload == sent_payload

        message.acknowledge()
        message_ids = recipient.list_messages()
        assert message_ids == []


def test_track_message_by_message_id(base_uri: str):
    workflow_id = uuid4().hex
    sent_payload = b"a" * 1000
    message_id = _mesh_client_send_message(base_uri, _CANNED_MAILBOX1, _CANNED_MAILBOX2, workflow_id, sent_payload)
    assert _mesh_client_get_inbox_count(base_uri, _CANNED_MAILBOX2) == 1

    tracking = _mesh_client_track_message_by_message_id(base_uri, _CANNED_MAILBOX1, message_id)
    assert tracking["message_id"] == message_id
    assert tracking["status"] == "accepted"
    # assert tracking["sender"] == _CANNED_MAILBOX1
    assert tracking["recipient"] == _CANNED_MAILBOX2

    with MeshClient(url=base_uri, mailbox=_CANNED_MAILBOX2, password=_PASSWORD, shared_key=_SHARED_KEY) as recipient:
        message = recipient.retrieve_message(message_id)
        message.acknowledge()

    tracking = _mesh_client_track_message_by_message_id(base_uri, _CANNED_MAILBOX1, message_id)
    assert tracking["message_id"] == message_id
    assert tracking["status"] == "acknowledged"
