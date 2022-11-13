import contextlib
import os
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi.testclient import TestClient

from ..common import MESH_AUTH_SCHEME, generate_cipher_text
from ..common.constants import Headers


def generate_auth_token(
    mailbox_id: str,
    mailbox_password: str = "password",
    secret_key: str = "TestKey",
    timestamp: str = None,
    nonce: str = None,
    nonce_count: str = "1",
) -> str:
    nonce = nonce or uuid4().hex
    timestamp = (timestamp or datetime.now()).strftime("%Y%m%d%H%M")
    public_auth_data = f"{mailbox_id}:{nonce}:{nonce_count}:{timestamp}"
    cipher_text = generate_cipher_text(secret_key, mailbox_id, mailbox_password, timestamp, nonce, nonce_count)
    return f"{MESH_AUTH_SCHEME} {public_auth_data}:{cipher_text}"


@contextlib.contextmanager
def temp_env_vars(**kwargs):
    """
    Temporarily set the process environment variables.
    >>> with temp_env_vars(PLUGINS_DIR=u'test/plugins'):
    ...   "PLUGINS_DIR" in os.environ
    True
    >>> "PLUGINS_DIR" in os.environ
    """
    old_environ = dict(os.environ)
    kwargs = {k: str(v) for k, v in kwargs.items()}
    os.environ.update(**kwargs)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_environ)


def send_message(
    app: TestClient,
    sender_mailbox_id: str,
    recipient_mailbox_id: str,
    workflow_id: str = None,
    message_data: bytes = None,
    extra_headers: dict = None,
    test_empty_payload: bool = False,
    file_name: Optional[str] = None,
):

    if not test_empty_payload:
        message_data = message_data or f"Hello World!\n{uuid4().hex}".encode("utf-8")

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

    response = app.post(f"/messageexchange/{sender_mailbox_id}/outbox", headers=headers, data=message_data)

    return response
