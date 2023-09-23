from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from ..common import APP_JSON, APP_V1_JSON, APP_V2_JSON
from ..common.constants import Headers
from ..tests.helpers import generate_auth_token, temp_env_vars

_CANNED_MAILBOX1 = "X26ABC1"
_CANNED_MAILBOX2 = "X26ABC2"


@pytest.mark.parametrize(
    ("mailbox_id", "accepts"),
    [
        (_CANNED_MAILBOX1, APP_JSON),
        (_CANNED_MAILBOX1, APP_V1_JSON),
        (_CANNED_MAILBOX1, APP_V2_JSON),
        (_CANNED_MAILBOX2, APP_JSON),
        (_CANNED_MAILBOX2, APP_V1_JSON),
        (_CANNED_MAILBOX2, APP_V2_JSON),
    ],
)
def test_handshake_no_auth_mailbox_exists(app: TestClient, mailbox_id: str, accepts: str):
    with temp_env_vars(AUTH_MODE="none"):
        res = app.get(
            f"/messageexchange/{mailbox_id}",
            headers={
                Headers.Accept: accepts,
                Headers.Mex_ClientVersion: "1.0",
                Headers.Mex_OSName: "bob",
                Headers.Mex_OSVersion: "latest",
            },
        )

        assert res.status_code == status.HTTP_200_OK

        if accepts == APP_V2_JSON:
            assert res.text == ""
        else:
            body = res.json()
            assert body["mailboxId"] == mailbox_id


@pytest.mark.parametrize(
    "accepts",
    [
        APP_JSON,
        APP_V1_JSON,
        APP_V2_JSON,
    ],
)
def test_handshake_no_auth_mailbox_does_not_exist(app: TestClient, accepts: str):
    with temp_env_vars(AUTH_MODE="none"):
        res = app.get(
            f"/messageexchange/{uuid4().hex}",
            headers={
                Headers.Mex_ClientVersion: "1.0",
                Headers.Mex_OSName: "bob",
                Headers.Mex_OSVersion: "latest",
                Headers.Accept: accepts,
            },
        )

        assert res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize(
    ("mailbox_id", "accepts"),
    [
        (_CANNED_MAILBOX1, APP_JSON),
        (_CANNED_MAILBOX1, APP_V1_JSON),
        (_CANNED_MAILBOX1, APP_V2_JSON),
        (_CANNED_MAILBOX2, APP_JSON),
        (_CANNED_MAILBOX2, APP_V1_JSON),
        (_CANNED_MAILBOX2, APP_V2_JSON),
    ],
)
def test_handshake_canned_auth_mailbox_exists(app: TestClient, mailbox_id: str, accepts: str):
    with temp_env_vars(AUTH_MODE="canned"):
        res = app.get(
            f"/messageexchange/{mailbox_id}",
            headers={
                Headers.Accept: accepts,
                Headers.Mex_ClientVersion: "1.0",
                Headers.Mex_OSName: "bob",
                Headers.Mex_OSVersion: "latest",
                Headers.Authorization: f"NHSMESH {mailbox_id}:VALID:1:things",
            },
        )

        assert res.status_code == status.HTTP_200_OK

        if accepts == APP_V2_JSON:
            assert res.text == ""
        else:
            body = res.json()
            assert body["mailboxId"] == mailbox_id


@pytest.mark.parametrize("mailbox_id", [_CANNED_MAILBOX1, _CANNED_MAILBOX2])
def test_handshake_canned_invalid_auth_mailbox_exists(app: TestClient, mailbox_id: str):
    with temp_env_vars(AUTH_MODE="canned"):
        res = app.get(
            f"/messageexchange/{mailbox_id}",
            headers={
                Headers.Mex_ClientVersion: "1.0",
                Headers.Mex_OSName: "bob",
                Headers.Mex_OSVersion: "latest",
                Headers.Authorization: f"NHSMESH {mailbox_id}:INVALID:1:things",
            },
        )

        assert res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize(
    ("mailbox_id", "accepts"),
    [
        (_CANNED_MAILBOX1, APP_JSON),
        (_CANNED_MAILBOX1, APP_V1_JSON),
        (_CANNED_MAILBOX1, APP_V2_JSON),
        (_CANNED_MAILBOX2, APP_JSON),
        (_CANNED_MAILBOX2, APP_V1_JSON),
        (_CANNED_MAILBOX2, APP_V2_JSON),
    ],
)
def test_handshake_full_auth_mailbox_exists(app: TestClient, mailbox_id: str, accepts: str):
    with temp_env_vars(AUTH_MODE="full"):
        res = app.get(
            f"/messageexchange/{mailbox_id}",
            headers={
                Headers.Accept: accepts,
                Headers.Mex_ClientVersion: "1.0",
                Headers.Mex_OSName: "bob",
                Headers.Mex_OSVersion: "latest",
                Headers.Authorization: generate_auth_token(mailbox_id, "password"),
            },
        )

        assert res.status_code == status.HTTP_200_OK

        if accepts == APP_V2_JSON:
            assert res.text == ""
        else:
            body = res.json()
            assert body["mailboxId"] == mailbox_id


def test_handshake_full_auth_mailbox_does_not_exist(app: TestClient):
    mailbox_id = uuid4().hex

    with temp_env_vars(AUTH_MODE="full"):
        res = app.get(
            f"/messageexchange/{mailbox_id}",
            headers={
                Headers.Mex_ClientVersion: "1.0",
                Headers.Mex_OSName: "bob",
                Headers.Mex_OSVersion: "latest",
                Headers.Authorization: generate_auth_token(mailbox_id, "password"),
            },
        )

        assert res.status_code == status.HTTP_403_FORBIDDEN


def test_handshake_full_auth_mailbox_bad_password(app: TestClient):
    mailbox_id = uuid4().hex

    with temp_env_vars(AUTH_MODE="full"):
        res = app.get(
            f"/messageexchange/{mailbox_id}",
            headers={
                Headers.Mex_ClientVersion: "1.0",
                Headers.Mex_OSName: "bob",
                Headers.Mex_OSVersion: "latest",
                Headers.Authorization: generate_auth_token(mailbox_id, "bad-password"),
            },
        )

        assert res.status_code == status.HTTP_403_FORBIDDEN


def test_handshake_full_auth_mailbox_bad_key(app: TestClient):
    mailbox_id = uuid4().hex

    with temp_env_vars(AUTH_MODE="full"):
        res = app.get(
            f"/messageexchange/{mailbox_id}",
            headers={
                Headers.Mex_ClientVersion: "1.0",
                Headers.Mex_OSName: "bob",
                Headers.Mex_OSVersion: "latest",
                Headers.Authorization: generate_auth_token(mailbox_id, "password", secret_key="BadKey"),
            },
        )

        assert res.status_code == status.HTTP_403_FORBIDDEN
