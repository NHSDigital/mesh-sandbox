import os
import shutil
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from mesh_sandbox.common import APP_V1_JSON
from mesh_sandbox.tests import _CANNED_MAILBOX1, _CANNED_MAILBOX2
from mesh_sandbox.tests.mesh_api_helpers import (
    mesh_api_get_inbox_size,
    mesh_api_send_message_and_return_message_id,
    mesh_api_track_message_by_message_id,
    mesh_api_track_message_by_message_id_status,
)

from ..common.constants import Headers
from ..models.message import MessageStatus, MessageType
from ..views.admin import AddMessageEventRequest, CreateReportRequest
from .helpers import generate_auth_token, temp_env_vars


def test_reset_canned_store_should_return_bad_request(app: TestClient):
    with temp_env_vars(STORE_MODE="canned"):
        res = app.delete("/messageexchange/admin/reset")
        assert res.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_reset_canned_store_with_valid_mailbox_id_should_return_bad_request(app: TestClient):
    with temp_env_vars(STORE_MODE="canned"):
        res = app.delete(f"/messageexchange/admin/reset/{_CANNED_MAILBOX1}")
        assert res.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_reset_memory_store_with_invalid_mailbox_id_should_return_bad_request(app: TestClient):
    with temp_env_vars(STORE_MODE="memory"):
        res = app.delete(f"/messageexchange/admin/reset/{uuid4().hex}")
        assert res.status_code == status.HTTP_404_NOT_FOUND


def test_reset_file_store_with_invalid_mailbox_id_should_return_bad_request(app: TestClient):
    with temp_env_vars(STORE_MODE="file"):
        res = app.delete(f"/messageexchange/admin/reset/{uuid4().hex}")
        assert res.status_code == status.HTTP_404_NOT_FOUND


def test_reset_memory_store_should_clear_all_mailboxes(app: TestClient):
    with temp_env_vars(STORE_MODE="memory"):
        msg_1to2_id = mesh_api_send_message_and_return_message_id(app, _CANNED_MAILBOX1, _CANNED_MAILBOX2)
        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX2) == 1

        msg_2to1_id = mesh_api_send_message_and_return_message_id(app, _CANNED_MAILBOX2, _CANNED_MAILBOX1)
        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX1) == 1

        res = app.delete("/messageexchange/admin/reset")
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

        res = app.get(
            f"/messageexchange/{_CANNED_MAILBOX1}/inbox/rich?max_results=10",
            headers={Headers.Authorization: generate_auth_token(_CANNED_MAILBOX1), Headers.Accept: APP_V1_JSON},
        )

        assert res.status_code == status.HTTP_200_OK
        response = res.json()
        messages = [res["message_id"] for res in response.get("messages", [])]
        assert len(messages) == 1

        res = app.get(
            f"/messageexchange/{_CANNED_MAILBOX2}/inbox/rich?max_results=10",
            headers={Headers.Authorization: generate_auth_token(_CANNED_MAILBOX2), Headers.Accept: APP_V1_JSON},
        )

        assert res.status_code == status.HTTP_200_OK
        response = res.json()
        messages = [res["message_id"] for res in response.get("messages", [])]
        assert len(messages) == 1

        # RESET mailbox 2
        res = app.delete(f"/messageexchange/admin/reset/{_CANNED_MAILBOX2}")
        assert res.status_code == status.HTTP_200_OK

        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX1) == 1
        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX2) == 0

        res = app.get(
            f"/messageexchange/{_CANNED_MAILBOX1}/inbox/rich?max_results=10",
            headers={Headers.Authorization: generate_auth_token(_CANNED_MAILBOX1), Headers.Accept: APP_V1_JSON},
        )

        assert res.status_code == status.HTTP_200_OK
        response = res.json()
        mb1_rich_inbox_messages = [res["message_id"] for res in response.get("messages", [])]
        assert len(mb1_rich_inbox_messages) == 1

        res = app.get(
            f"/messageexchange/{_CANNED_MAILBOX2}/inbox/rich?max_results=10",
            headers={Headers.Authorization: generate_auth_token(_CANNED_MAILBOX2), Headers.Accept: APP_V1_JSON},
        )

        assert res.status_code == status.HTTP_200_OK
        response = res.json()
        mb2_rich_inbox_messages = [res["message_id"] for res in response.get("messages", [])]
        assert len(mb2_rich_inbox_messages) == 0


def test_reset_file_store_should_clear_all_mailboxes_and_maybe_files(app: TestClient, tmp_path: str):
    with temp_env_vars(STORE_MODE="file", MAILBOXES_DATA_DIR=tmp_path):
        msg_1to2_id = mesh_api_send_message_and_return_message_id(app, _CANNED_MAILBOX1, _CANNED_MAILBOX2)
        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX2) == 1

        msg_2to1_id = mesh_api_send_message_and_return_message_id(app, _CANNED_MAILBOX2, _CANNED_MAILBOX1)
        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX1) == 1

        inbox_folder1 = os.path.join(tmp_path, _CANNED_MAILBOX1, "in")
        assert os.path.exists(inbox_folder1)
        all_files = os.listdir(inbox_folder1)
        messages = [msg for msg in all_files if not msg.endswith(".json")]
        assert {msg[:-5] for msg in all_files if msg.endswith(".json")} == set(messages)
        assert len(messages) == 1
        assert messages[0] == msg_2to1_id

        inbox_folder2 = os.path.join(tmp_path, _CANNED_MAILBOX2, "in")
        assert os.path.exists(inbox_folder2)
        all_files = os.listdir(inbox_folder2)
        messages = [msg for msg in all_files if not msg.endswith(".json")]
        assert {msg[:-5] for msg in all_files if msg.endswith(".json")} == set(messages)
        assert len(messages) == 1
        assert messages[0] == msg_1to2_id

        shutil.rmtree(inbox_folder1)
        shutil.rmtree(inbox_folder2)

        res = app.delete("/messageexchange/admin/reset")
        assert res.status_code == status.HTTP_200_OK

        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX1) == 0
        assert (
            mesh_api_track_message_by_message_id_status(app, _CANNED_MAILBOX1, msg_1to2_id) == status.HTTP_404_NOT_FOUND
        )

        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX2) == 0
        assert (
            mesh_api_track_message_by_message_id_status(app, _CANNED_MAILBOX2, msg_2to1_id) == status.HTTP_404_NOT_FOUND
        )


def test_reset_file_store_should_clear_specified_mailbox_only_and_maybe_files(app: TestClient, tmp_path: str):
    with temp_env_vars(STORE_MODE="file", MAILBOXES_DATA_DIR=tmp_path):
        msg_1to2_id = mesh_api_send_message_and_return_message_id(app, _CANNED_MAILBOX1, _CANNED_MAILBOX2)
        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX2) == 1

        msg_2to1_id = mesh_api_send_message_and_return_message_id(app, _CANNED_MAILBOX2, _CANNED_MAILBOX1)
        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX1) == 1

        inbox_folder1 = os.path.join(tmp_path, _CANNED_MAILBOX1, "in")
        assert os.path.exists(inbox_folder1)
        all_files = os.listdir(inbox_folder1)
        messages = [msg for msg in all_files if not msg.endswith(".json")]
        assert {msg[:-5] for msg in all_files if msg.endswith(".json")} == set(messages)
        assert len(messages) == 1
        assert messages[0] == msg_2to1_id

        inbox_folder2 = os.path.join(tmp_path, _CANNED_MAILBOX2, "in")
        assert os.path.exists(inbox_folder2)
        all_files = os.listdir(inbox_folder2)
        messages = [msg for msg in all_files if not msg.endswith(".json")]
        assert {msg[:-5] for msg in all_files if msg.endswith(".json")} == set(messages)
        assert len(messages) == 1
        assert messages[0] == msg_1to2_id

        res = app.delete(f"/messageexchange/admin/reset/{_CANNED_MAILBOX2}")
        assert res.status_code == status.HTTP_200_OK

        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX1) == 1
        assert mesh_api_get_inbox_size(app, _CANNED_MAILBOX2) == 0

        assert os.path.exists(inbox_folder1)
        assert os.path.exists(inbox_folder2)


@pytest.mark.parametrize("clear_disk", ["tRue", "faLse", None])
def test_reset_file_store_should_not_error_if_folder_does_not_exist_yet(
    app: TestClient, clear_disk: str, tmp_path: str
):
    with temp_env_vars(STORE_MODE="file", MAILBOXES_DATA_DIR=tmp_path):
        inbox_folder = os.path.join(tmp_path, _CANNED_MAILBOX1, "in")
        assert not os.path.exists(inbox_folder)

        clear_disk_param = "" if clear_disk is None else f"?clear_disk={clear_disk}"
        res = app.delete(f"/messageexchange/admin/reset/{_CANNED_MAILBOX2}{clear_disk_param}")
        assert res.status_code == status.HTTP_200_OK


def test_put_report_in_inbox(app: TestClient, tmp_path: str):
    recipient = _CANNED_MAILBOX1

    with temp_env_vars(STORE_MODE="file", MAILBOXES_DATA_DIR=tmp_path):
        request = CreateReportRequest(
            mailbox_id=recipient,
            status=MessageStatus.ERROR,
            workflow_id=uuid4().hex,
            code="21",
            description="my error",
            subject=f"my subject {uuid4().hex}",
            local_id=f"my local id {uuid4().hex}",
            file_name=f"my filename {uuid4().hex}",
            linked_message_id=uuid4().hex,
        )

        res = app.post("/messageexchange/admin/report", json=request.dict())
        assert res.status_code == status.HTTP_200_OK

        result = res.json()
        assert result
        message_id = result["message_id"]
        assert message_id

        res = app.get(
            f"/messageexchange/{recipient}/inbox",
            headers={Headers.Authorization: generate_auth_token(recipient)},
        )
        messages = res.json().get("messages", [])
        assert messages
        assert messages[0] == message_id

        res = app.get(
            f"/messageexchange/{recipient}/inbox/{message_id}",
            headers={Headers.Authorization: generate_auth_token(recipient)},
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.text == ""
        assert res.headers.get(Headers.Mex_To) == recipient
        assert res.headers.get(Headers.Mex_WorkflowID) == request.workflow_id
        assert res.headers.get(Headers.Mex_MessageType) == MessageType.REPORT
        assert res.headers.get(Headers.Mex_StatusCode) == request.code
        assert res.headers.get(Headers.Mex_StatusDescription) == request.description
        assert res.headers.get(Headers.Mex_FileName) == request.file_name
        assert res.headers.get(Headers.Mex_LinkedMsgId) == request.linked_message_id
        assert res.headers.get(Headers.Mex_LocalID) == request.local_id
        assert res.headers.get(Headers.Mex_StatusSuccess) == "ERROR"
        assert res.headers.get(Headers.Content_Length) == "0"

        res = app.put(
            f"/messageexchange/{recipient}/inbox/{message_id}/status/acknowledged",
            headers={Headers.Authorization: generate_auth_token(recipient)},
        )
        assert res.status_code == status.HTTP_200_OK

        res = app.get(
            f"/messageexchange/{recipient}/inbox",
            headers={Headers.Authorization: generate_auth_token(recipient)},
        )
        messages = res.json().get("messages", [])
        assert not messages


def test_add_message_event(app: TestClient, tmp_path: str):
    recipient = _CANNED_MAILBOX1

    with temp_env_vars(STORE_MODE="file", MAILBOXES_DATA_DIR=tmp_path):
        create_report_request = CreateReportRequest(
            mailbox_id=recipient,
            status=MessageStatus.ERROR,
            workflow_id=uuid4().hex,
            code="21",
            description="my error",
            subject=f"my subject {uuid4().hex}",
            local_id=f"my local id {uuid4().hex}",
            file_name=f"my filename {uuid4().hex}",
            linked_message_id=uuid4().hex,
        )

        res = app.post("/messageexchange/admin/report", json=create_report_request.dict())
        assert res.status_code == status.HTTP_200_OK

        result = res.json()
        assert result
        message_id = result["message_id"]
        assert message_id

        res = app.get(
            f"/messageexchange/{recipient}/inbox",
            headers={Headers.Authorization: generate_auth_token(recipient)},
        )
        messages = res.json().get("messages", [])
        assert messages
        assert messages[0] == message_id

        res = app.put(
            f"/messageexchange/{recipient}/inbox/{message_id}/status/acknowledged",
            headers={Headers.Authorization: generate_auth_token(recipient)},
        )
        assert res.status_code == status.HTTP_200_OK

        res = app.get(
            f"/messageexchange/{recipient}/inbox",
            headers={Headers.Authorization: generate_auth_token(recipient)},
        )
        messages = res.json().get("messages", [])
        assert not messages

        # move the message to accepted again
        add_event_request = AddMessageEventRequest(status=MessageStatus.ACCEPTED)

        res = app.post(f"/messageexchange/admin/message/{message_id}/event", json=add_event_request.dict())
        assert res.status_code == status.HTTP_200_OK

        res = app.get(
            f"/messageexchange/{recipient}/inbox",
            headers={Headers.Authorization: generate_auth_token(recipient)},
        )
        messages = res.json().get("messages", [])
        assert messages == [message_id]


@pytest.mark.parametrize("root_path", ["/admin/mailbox", "/messageexchange/admin/mailbox", "/messageexchange/mailbox"])
def test_get_mailbox_invalid_mailbox_returns_404(app: TestClient, root_path: str):
    with temp_env_vars(STORE_MODE="canned"):
        res = app.get(f"{root_path}/NotAMailboxId")
        assert res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize("root_path", ["/admin/mailbox", "/messageexchange/admin/mailbox", "/messageexchange/mailbox"])
def test_get_mailbox_happy_path(app: TestClient, root_path: str):
    with temp_env_vars(STORE_MODE="canned"):
        res = app.get(f"{root_path}/{_CANNED_MAILBOX1}")
        assert res.status_code == status.HTTP_200_OK

        get_mailbox = res.json()
        assert len(get_mailbox) == 7

        assert get_mailbox["mailbox_id"] == _CANNED_MAILBOX1
        assert get_mailbox["mailbox_name"] == "TESTMB1"
        assert get_mailbox["billing_entity"] == "England"
        assert get_mailbox["ods_code"] == "X26"
        assert get_mailbox["org_code"] == "X26"
        assert get_mailbox["org_name"] == ""
        assert get_mailbox["active"] is True


@pytest.mark.parametrize("root_path", ["/admin/message", "/messageexchange/admin/message"])
def test_get_message(app: TestClient, root_path: str):
    message_data = b"Hello World123!"
    msg_id = mesh_api_send_message_and_return_message_id(
        app, _CANNED_MAILBOX1, _CANNED_MAILBOX2, file_name="helloworld.dat", message_data=message_data
    )
    res = app.get(f"{root_path}/{msg_id}")

    assert res.status_code == status.HTTP_200_OK

    message = res.json()
    upload_date = datetime.now()
    expiry_date = upload_date + timedelta(days=5)

    assert message["checksum"] == ""
    assert message["chunk_count"] == 1
    assert message["content_encoding"] == ""
    assert message["expiry_time"].startswith(expiry_date.strftime("%Y-%m-%d"))
    assert message["filename"] == "helloworld.dat"
    assert message["file_size"] == 15
    assert not message["is_compressed"]
    assert not message["is_encrypted"]
    assert message["local_id"] == ""
    assert message["message_id"] == msg_id
    assert message["message_type"] == "Data"
    assert message["recipient"] == _CANNED_MAILBOX2
    assert message["recipient_ods_code"] == "X26"
    assert message["recipient_org_code"] == "X26"
    assert message["sender"] == _CANNED_MAILBOX1
    assert message["sender_ods_code"] == "X26"
    assert message["sender_org_code"] == "X26"
    assert message["status"] == "Accepted"
    assert message["status_success"] == "SUCCESS"
    assert message["subject"] == ""
    assert message["upload_timestamp"].startswith(upload_date.strftime("%Y-%m-%d"))
    assert message["workflow_id"] == "TEST_WORKFLOW"


@pytest.mark.parametrize("root_path", ["/admin/message", "/messageexchange/admin/message"])
def test_get_message_report_type(app: TestClient, root_path: str):
    expected_response = {
        "status": MessageStatus.ERROR,
        "workflow_id": uuid4().hex,
        "code": "21",
        "description": "my error",
        "subject": f"my subject {uuid4().hex}",
        "local_id": f"my local id {uuid4().hex}",
        "file_name": f"my filename {uuid4().hex}",
        "linked_message_id": uuid4().hex,
    }

    request = CreateReportRequest(
        mailbox_id=_CANNED_MAILBOX1,
        status=expected_response["status"],
        workflow_id=expected_response["workflow_id"],
        code=expected_response["code"],
        description=expected_response["description"],
        subject=expected_response["subject"],
        local_id=expected_response["local_id"],
        file_name=expected_response["file_name"],
        linked_message_id=expected_response["linked_message_id"],
    )

    res = app.post("/messageexchange/admin/report", json=request.dict())
    assert res.status_code == status.HTTP_200_OK
    msg_id = res.json()["message_id"]

    res = app.get(f"{root_path}/{msg_id}")
    message = res.json()

    assert message["message_id"] == msg_id
    assert message["linked_msg_id"] == expected_response["linked_message_id"]
    assert message["message_type"] == "Report"
    assert message["recipient"] == _CANNED_MAILBOX1
    assert message["status_code"] == expected_response["code"]
    assert message["status_success"] == "ERROR"


@pytest.mark.parametrize("root_path", ["/admin/message", "/messageexchange/admin/message", "/messageexchange/message"])
def test_get_message_not_found(app: TestClient, root_path: str):
    res = app.get(f"{root_path}/notfound")
    assert res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize("root_path", ["/messageexchange/admin/message"])
def test_generate_ndr(app: TestClient, root_path: str):

    expected_response = {
        "status": MessageStatus.UNDELIVERABLE,
        "workflow_id": uuid4().hex,
        "code": "21",
        "description": "non delivery reason",
        "subject": f"my subject {uuid4().hex}",
        "local_id": f"my local id {uuid4().hex}",
        "file_name": f"my filename {uuid4().hex}",
        "linked_message_id": uuid4().hex,
    }

    request = CreateReportRequest(
        mailbox_id=_CANNED_MAILBOX1,
        code=expected_response["code"],
        description=expected_response["description"],
        workflow_id=expected_response["workflow_id"],
        subject=expected_response["subject"],
        local_id=expected_response["local_id"],
        status=expected_response["status"],
        file_name=expected_response["file_name"],
        linked_message_id=expected_response["linked_message_id"],
    )

    res = app.post("/messageexchange/admin/report", json=request.model_dump())
    assert res.status_code == status.HTTP_200_OK
    msg_id = res.json()["message_id"]

    res = app.get(f"{root_path}/{msg_id}")
    non_delivery_report = res.json()
    assert non_delivery_report["status"] == "Accepted"
    assert non_delivery_report["status_description"] == "Message not collected by recipient after 5 days"
