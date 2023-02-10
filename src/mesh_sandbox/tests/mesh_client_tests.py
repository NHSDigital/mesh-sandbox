import os
from uuid import uuid4

import httpx
import pytest
from fastapi import status
from mesh_client import MeshClient
from requests.models import HTTPError

from .helpers import temp_env_vars

_CANNED_MAILBOX1 = "X26ABC1"
_CANNED_MAILBOX2 = "X26ABC2"
_SHARED_KEY = b"TestKey"
_PASSWORD = "password"


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
        assert err.value.response.status_code == status.HTTP_400_BAD_REQUEST


def _send_message_and_assert_inbox_count_is_one(
    base_uri: str, recipient_mailbox_id: str, workflow_id: str, payload: bytes
):
    sender_mailbox_id = _CANNED_MAILBOX1

    with MeshClient(
        url=base_uri, mailbox=sender_mailbox_id, password=_PASSWORD, shared_key=_SHARED_KEY, max_chunk_size=100
    ) as sender:

        message_id = sender.send_message(recipient_mailbox_id, payload, workflow_id=workflow_id)
        assert message_id
        assert _get_inbox_count(base_uri, _CANNED_MAILBOX2) == 1
        return message_id


def test_send_receive_chunked_message(base_uri: str):

    recipient_mailbox_id = _CANNED_MAILBOX2
    workflow_id = uuid4().hex
    sent_payload = b"a" * 1000
    message_id = _send_message_and_assert_inbox_count_is_one(base_uri, recipient_mailbox_id, workflow_id, sent_payload)

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


def _get_inbox_count(base_uri: str, recipient_mailbox_id: str):
    with MeshClient(
        url=base_uri, mailbox=recipient_mailbox_id, password=_PASSWORD, shared_key=_SHARED_KEY
    ) as recipient:
        message_ids = recipient.list_messages()
        return len(message_ids)


def test_reset_memory_store_should_clear_inbox(base_uri: str):

    _send_message_and_assert_inbox_count_is_one(base_uri, _CANNED_MAILBOX2, uuid4().hex, b"b" * 10)

    with temp_env_vars(STORE_MODE="memory"):
        with httpx.Client(base_url=base_uri) as client:
            res = client.get("/reset")
            assert res.status_code == status.HTTP_200_OK

    assert _get_inbox_count(base_uri, _CANNED_MAILBOX2) == 0


@pytest.mark.parametrize("clear_disk", ["tRue", "faLse", None])
def test_reset_file_store_should_clear_inbox_and_maybe_files(base_uri: str, clear_disk: str, tmp_path: str):

    with temp_env_vars(STORE_MODE="file", FILE_STORE_DIR=tmp_path):

        message_id = _send_message_and_assert_inbox_count_is_one(base_uri, _CANNED_MAILBOX2, uuid4().hex, b"b" * 10)

        inbox_folder = os.path.join(tmp_path, _CANNED_MAILBOX2, "in")
        assert os.path.exists(inbox_folder)
        messages = os.listdir(inbox_folder)
        assert len(messages) == 1
        assert messages[0] == message_id

        with httpx.Client(base_url=base_uri, timeout=60) as client:
            clear_disk_param = "" if clear_disk is None else f"?clear_disk={clear_disk}"
            res = client.get(f"/reset{clear_disk_param}")
            assert res.status_code == status.HTTP_200_OK

        assert _get_inbox_count(base_uri, _CANNED_MAILBOX2) == 0

        # clear_disk should default to true if file mode is used
        if not clear_disk or clear_disk == "tRue":
            assert not os.path.exists(inbox_folder)


def test_reset_canned_store_should_return_bad_request(base_uri: str):

    with temp_env_vars(STORE_MODE="canned"):
        with httpx.Client(base_url=base_uri) as client:
            res = client.get("/reset")
            assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_reset_memory_store_with_clear_disk_should_return_bad_request(base_uri: str):

    with temp_env_vars(STORE_MODE="memory"):
        with httpx.Client(base_url=base_uri) as client:
            res = client.get("/reset?clear_disk=true")
            assert res.status_code == status.HTTP_400_BAD_REQUEST
