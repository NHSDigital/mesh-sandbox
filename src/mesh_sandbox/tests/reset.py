import os
from uuid import uuid4

import httpx
import pytest
from fastapi import status

from mesh_sandbox.tests import _CANNED_MAILBOX2
from mesh_sandbox.tests.mesh_client_tests import (
    _get_inbox_count,
    _send_message_and_assert_inbox_count_is_one,
)

from .helpers import temp_env_vars


def test_reset_memory_store_should_clear_inbox(base_uri: str):

    _send_message_and_assert_inbox_count_is_one(base_uri, _CANNED_MAILBOX2, uuid4().hex, b"b" * 10)

    with temp_env_vars(STORE_MODE="memory"):
        with httpx.Client(base_url=base_uri) as client:
            res = client.get("/messageexchange/reset")
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
            res = client.get(f"/messageexchange/reset{clear_disk_param}")
            assert res.status_code == status.HTTP_200_OK

        assert _get_inbox_count(base_uri, _CANNED_MAILBOX2) == 0

        # clear_disk should default to true if file mode is used
        if not clear_disk or clear_disk == "tRue":
            assert not os.path.exists(inbox_folder)


def test_reset_canned_store_should_return_bad_request(base_uri: str):

    with temp_env_vars(STORE_MODE="canned"):
        with httpx.Client(base_url=base_uri) as client:
            res = client.get("/messageexchange/reset")
            assert res.status_code == status.HTTP_400_BAD_REQUEST
