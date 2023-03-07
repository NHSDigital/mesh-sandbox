import os
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from mesh_sandbox.tests import _CANNED_MAILBOX1, _CANNED_MAILBOX2
from mesh_sandbox.tests.mesh_api_helpers import (
    mesh_api_get_inbox_size,
    mesh_api_send_message_and_return_message_id,
    mesh_api_track_message_by_message_id,
    mesh_api_track_message_by_message_id_status,
)

from .helpers import temp_env_vars


def test_reset_canned_store_should_return_bad_request(app: TestClient):

    with temp_env_vars(STORE_MODE="canned"):

        res = app.get("/messageexchange/reset")
        assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_reset_canned_store_with_valid_mailbox_id_should_return_bad_request(app: TestClient):

    with temp_env_vars(STORE_MODE="canned"):

        res = app.get(f"/messageexchange/reset/{_CANNED_MAILBOX1}")
        assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_reset_memory_store_with_invalid_mailbox_id_should_return_bad_request(app: TestClient):

    with temp_env_vars(STORE_MODE="memory"):

        res = app.get(f"/messageexchange/reset/{uuid4().hex}")
        assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_reset_file_store_with_invalid_mailbox_id_should_return_bad_request(app: TestClient):

    with temp_env_vars(STORE_MODE="file"):

        res = app.get(f"/messageexchange/reset/{uuid4().hex}")
        assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_reset_memory_store_should_clear_all_mailboxes(app: TestClient):

    with temp_env_vars(STORE_MODE="memory"):

        msg_1to2_id = mesh_api_send_message_and_return_message_id(app, _CANNED_MAILBOX1, _CANNED_MAILBOX2)
        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX2) == 1

        msg_2to1_id = mesh_api_send_message_and_return_message_id(app, _CANNED_MAILBOX2, _CANNED_MAILBOX1)
        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX1) == 1

        res = app.get("/messageexchange/reset")
        assert res.status_code == status.HTTP_200_OK

        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX1) == 0
        assert (
            mesh_api_track_message_by_message_id_status(app, _CANNED_MAILBOX1, msg_2to1_id) == status.HTTP_404_NOT_FOUND
        )

        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX2) == 0
        assert (
            mesh_api_track_message_by_message_id_status(app, _CANNED_MAILBOX2, msg_1to2_id) == status.HTTP_404_NOT_FOUND
        )


def test_reset_memory_store_should_clear_specified_mailbox_only(app: TestClient):

    with temp_env_vars(STORE_MODE="memory"):

        msg_1to2_id = mesh_api_send_message_and_return_message_id(app, _CANNED_MAILBOX1, _CANNED_MAILBOX2)
        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX2) == 1

        res = mesh_api_track_message_by_message_id(app, _CANNED_MAILBOX1, msg_1to2_id)
        assert res.json()["messageId"] == msg_1to2_id

        msg_2to1_id = mesh_api_send_message_and_return_message_id(app, _CANNED_MAILBOX2, _CANNED_MAILBOX1)
        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX1) == 1

        res = mesh_api_track_message_by_message_id(app, _CANNED_MAILBOX2, msg_2to1_id)
        assert res.json()["messageId"] == msg_2to1_id

        res = app.get(f"/messageexchange/reset/{_CANNED_MAILBOX2}")
        assert res.status_code == status.HTTP_200_OK

        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX2) == 0
        assert (
            mesh_api_track_message_by_message_id_status(app, _CANNED_MAILBOX2, msg_2to1_id) == status.HTTP_404_NOT_FOUND
        )

        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX1) == 1
        assert mesh_api_track_message_by_message_id_status(app, _CANNED_MAILBOX1, msg_1to2_id) == status.HTTP_200_OK


@pytest.mark.parametrize("clear_disk", ["tRue", "faLse", None])
def test_reset_file_store_should_clear_all_mailboxes_and_maybe_files(app: TestClient, clear_disk: str, tmp_path: str):

    with temp_env_vars(STORE_MODE="file", FILE_STORE_DIR=tmp_path):

        msg_1to2_id = mesh_api_send_message_and_return_message_id(app, _CANNED_MAILBOX1, _CANNED_MAILBOX2)
        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX2) == 1

        msg_2to1_id = mesh_api_send_message_and_return_message_id(app, _CANNED_MAILBOX2, _CANNED_MAILBOX1)
        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX1) == 1

        inbox_folder1 = os.path.join(tmp_path, _CANNED_MAILBOX1, "in")
        assert os.path.exists(inbox_folder1)
        messages = os.listdir(inbox_folder1)
        assert len(messages) == 1
        assert messages[0] == msg_2to1_id

        inbox_folder2 = os.path.join(tmp_path, _CANNED_MAILBOX2, "in")
        assert os.path.exists(inbox_folder2)
        messages = os.listdir(inbox_folder2)
        assert len(messages) == 1
        assert messages[0] == msg_1to2_id

        clear_disk_param = "" if clear_disk is None else f"?clear_disk={clear_disk}"
        res = app.get(f"/messageexchange/reset{clear_disk_param}")
        assert res.status_code == status.HTTP_200_OK

        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX1) == 0
        assert (
            mesh_api_track_message_by_message_id_status(app, _CANNED_MAILBOX1, msg_1to2_id) == status.HTTP_404_NOT_FOUND
        )

        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX2) == 0
        assert (
            mesh_api_track_message_by_message_id_status(app, _CANNED_MAILBOX2, msg_2to1_id) == status.HTTP_404_NOT_FOUND
        )

        # clear_disk should default to true if file mode is used
        if not clear_disk or clear_disk == "tRue":
            assert not os.path.exists(inbox_folder1)
            assert not os.path.exists(inbox_folder2)


@pytest.mark.parametrize("clear_disk", ["tRue", "faLse", None])
def test_reset_file_store_should_clear_specified_mailbox_only_and_maybe_files(
    app: TestClient, clear_disk: str, tmp_path: str
):

    with temp_env_vars(STORE_MODE="file", FILE_STORE_DIR=tmp_path):

        msg_1to2_id = mesh_api_send_message_and_return_message_id(app, _CANNED_MAILBOX1, _CANNED_MAILBOX2)
        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX2) == 1

        msg_2to1_id = mesh_api_send_message_and_return_message_id(app, _CANNED_MAILBOX2, _CANNED_MAILBOX1)
        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX1) == 1

        inbox_folder1 = os.path.join(tmp_path, _CANNED_MAILBOX1, "in")
        assert os.path.exists(inbox_folder1)
        messages = os.listdir(inbox_folder1)
        assert len(messages) == 1
        assert messages[0] == msg_2to1_id

        inbox_folder2 = os.path.join(tmp_path, _CANNED_MAILBOX2, "in")
        assert os.path.exists(inbox_folder2)
        messages = os.listdir(inbox_folder2)
        assert len(messages) == 1
        assert messages[0] == msg_1to2_id

        clear_disk_param = "" if clear_disk is None else f"?clear_disk={clear_disk}"
        res = app.get(f"/messageexchange/reset/{_CANNED_MAILBOX2}{clear_disk_param}")
        assert res.status_code == status.HTTP_200_OK

        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX1) == 1
        assert mesh_api_track_message_by_message_id_status(app, _CANNED_MAILBOX1, msg_1to2_id) == status.HTTP_200_OK

        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX2) == 0
        assert (
            mesh_api_track_message_by_message_id_status(app, _CANNED_MAILBOX2, msg_2to1_id) == status.HTTP_404_NOT_FOUND
        )

        # clear_disk should default to true if file mode is used
        if not clear_disk or clear_disk == "tRue":
            assert os.path.exists(inbox_folder1)
            assert not os.path.exists(inbox_folder2)


@pytest.mark.parametrize("clear_disk", ["tRue", "faLse", None])
def test_reset_file_store_should_not_error_if_folder_does_not_exist_yet(
    app: TestClient, clear_disk: str, tmp_path: str
):

    with temp_env_vars(STORE_MODE="file", FILE_STORE_DIR=tmp_path):

        inbox_folder = os.path.join(tmp_path, _CANNED_MAILBOX1, "in")
        assert not os.path.exists(inbox_folder)

        clear_disk_param = "" if clear_disk is None else f"?clear_disk={clear_disk}"
        res = app.get(f"/messageexchange/reset/{_CANNED_MAILBOX2}{clear_disk_param}")
        assert res.status_code == status.HTTP_200_OK
