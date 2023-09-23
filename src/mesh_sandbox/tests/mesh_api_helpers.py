from typing import Optional
from uuid import uuid4

from fastapi.testclient import TestClient

from mesh_sandbox.tests.helpers import generate_auth_token

from ..common.constants import Headers


def mesh_api_send_message(
    app: TestClient,
    sender_mailbox_id: str,
    recipient_mailbox_id: str,
    message_data: Optional[bytes] = None,
    workflow_id: Optional[str] = None,
    extra_headers: Optional[dict] = None,
    test_empty_message_data: bool = False,
    file_name: Optional[str] = None,
):
    if not test_empty_message_data:
        message_data = message_data or f"Hello World!\n{uuid4().hex}".encode()

    headers = {
        Headers.Mex_From: sender_mailbox_id,
        Headers.Mex_To: recipient_mailbox_id,
        Headers.Mex_WorkflowID: workflow_id or "TEST_WORKFLOW",
        Headers.Authorization: generate_auth_token(sender_mailbox_id),
    }

    if file_name:
        headers[Headers.Mex_FileName] = file_name

    if extra_headers:
        headers.update(extra_headers)

    return app.post(f"/messageexchange/{sender_mailbox_id}/outbox", headers=headers, content=message_data)


def mesh_api_send_message_and_return_message_id(
    app: TestClient,
    sender_mailbox_id: str,
    recipient_mailbox_id: str,
    message_data: Optional[bytes] = None,
    workflow_id: Optional[str] = None,
    extra_headers: Optional[dict] = None,
    test_empty_message_data: bool = False,
    file_name: Optional[str] = None,
):
    res = mesh_api_send_message(
        app,
        sender_mailbox_id,
        recipient_mailbox_id,
        message_data,
        workflow_id,
        extra_headers,
        test_empty_message_data,
        file_name,
    )

    assert res.status_code == 202, res.text
    return res.json()["messageID"]


def mesh_api_get_message(
    app: TestClient,
    recipient_mailbox_id: str,
    message_id: str,
    extra_headers: Optional[dict] = None,
):
    headers = {Headers.Authorization: generate_auth_token(recipient_mailbox_id)}
    if extra_headers:
        headers.update(extra_headers)

    return app.get(url=f"/messageexchange/{recipient_mailbox_id}/inbox/{message_id}", headers=headers)


def mesh_api_get_inbox(
    app: TestClient,
    recipient_mailbox_id: str,
    extra_headers: Optional[dict] = None,
):
    headers = {Headers.Authorization: generate_auth_token(recipient_mailbox_id)}
    if extra_headers:
        headers.update(extra_headers)

    return app.get(url=f"/messageexchange/{recipient_mailbox_id}/inbox", headers=headers)


def mesh_api_get_inbox_size(
    app: TestClient,
    recipient_mailbox_id: str,
    extra_headers: Optional[dict] = None,
):
    res = mesh_api_get_inbox(app, recipient_mailbox_id, extra_headers=extra_headers)
    assert res.status_code == 200
    return len(res.json()["messages"])


def mesh_api_track_message_by_local_id(
    app: TestClient, sender_mailbox_id: str, local_id: str, extra_headers: Optional[dict] = None
):
    headers = {Headers.Authorization: generate_auth_token(sender_mailbox_id)}
    if extra_headers:
        headers.update(extra_headers)

    return app.get(f"/messageexchange/{sender_mailbox_id}/outbox/tracking?localID={local_id}", headers=headers)


def mesh_api_track_message_by_message_id(
    app: TestClient, sender_mailbox_id: str, message_id: str, extra_headers: Optional[dict] = None
):
    headers = {Headers.Authorization: generate_auth_token(sender_mailbox_id)}
    if extra_headers:
        headers.update(extra_headers)

    res = app.get(f"/messageexchange/{sender_mailbox_id}/outbox/tracking?messageID={message_id}", headers=headers)
    return res


def mesh_api_track_message_by_message_id_status(
    app: TestClient, sender_mailbox_id: str, message_id: str, extra_headers: Optional[dict] = None
):
    res = mesh_api_track_message_by_message_id(app, sender_mailbox_id, message_id, extra_headers=extra_headers)
    return res.status_code
