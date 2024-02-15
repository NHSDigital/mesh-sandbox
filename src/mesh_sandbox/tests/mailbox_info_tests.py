from fastapi import status
from fastapi.testclient import TestClient

from mesh_sandbox.tests import _CANNED_MAILBOX1

from .helpers import temp_env_vars


def test_get_mailbox_invalid_mailbox_returns_404(app: TestClient):
    with temp_env_vars(STORE_MODE="canned"):
        res = app.get("/messageexchange/mailbox/NotAMailboxId")
        assert res.status_code == status.HTTP_404_NOT_FOUND


def test_get_mailbox_happy_path(app: TestClient):
    with temp_env_vars(STORE_MODE="canned"):
        res = app.get(f"/messageexchange/mailbox/{_CANNED_MAILBOX1}")
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
