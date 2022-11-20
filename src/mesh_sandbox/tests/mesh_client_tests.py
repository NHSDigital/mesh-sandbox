from uuid import uuid4

import httpx
import pytest
from fastapi import status
from mesh_client import MeshClient
from requests.models import HTTPError


def test_app_health(base_uri: str):

    with httpx.Client(base_url=base_uri) as client:
        res = client.get("/health")
        assert res.status_code == status.HTTP_200_OK


_CANNED_MAILBOX1 = "X26ABC1"
_CANNED_MAILBOX2 = "X26ABC2"
_SHARED_KEY = b"TestKey"
_PASSWORD = "password"


def test_handshake(base_uri: str):

    with MeshClient(url=base_uri, mailbox=_CANNED_MAILBOX1, password=_PASSWORD, shared_key=_SHARED_KEY) as client:
        res = client.handshake()
        assert res == b"hello"


def test_handshake_bad_password(base_uri: str):

    with MeshClient(url=base_uri, mailbox=_CANNED_MAILBOX1, password="BAD", shared_key=_SHARED_KEY) as client:

        with pytest.raises(HTTPError) as err:
            client.handshake()
        assert err.value.response.status_code == status.HTTP_400_BAD_REQUEST


def test_send_receive_chunked_message(base_uri: str):

    sender_mailbox_id = _CANNED_MAILBOX1
    recipient_mailbox_id = _CANNED_MAILBOX2
    workflow_id = uuid4().hex

    with MeshClient(
        url=base_uri, mailbox=sender_mailbox_id, password=_PASSWORD, shared_key=_SHARED_KEY, max_chunk_size=100
    ) as sender:

        sent_payload = b"a" * 1000

        message_id = sender.send_message(_CANNED_MAILBOX2, sent_payload, workflow_id=workflow_id)

        assert message_id

        with MeshClient(
            url=base_uri, mailbox=recipient_mailbox_id, password=_PASSWORD, shared_key=_SHARED_KEY
        ) as recipient:
            message_ids = recipient.list_messages()
            assert message_ids == [message_id]
            message = recipient.retrieve_message(message_id)
            assert message.workflow_id == workflow_id  # pylint: disable=no-member
            received_payload = message.read()
            assert received_payload == sent_payload

            message.acknowledge()
            message_ids = recipient.list_messages()
            assert message_ids == []
