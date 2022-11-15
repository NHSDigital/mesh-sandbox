from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from ..common import APP_V1_JSON, APP_V2_JSON
from ..common.constants import Headers

_CANNED_MAILBOX1 = "X26ABC1"
_CANNED_MAILBOX2 = "X26ABC2"
_CANNED_MAILBOX3 = "X26ABC3"


@pytest.mark.parametrize(
    "workflow_id, ods_code, accepts, expected",
    [
        ("TEST_WORKFLOW", "X26", APP_V1_JSON, {_CANNED_MAILBOX2}),
        ("TEST_WORKFLOW", "X26", APP_V2_JSON, {_CANNED_MAILBOX2}),
        ("TEST_WORKFLOW", "X27", APP_V1_JSON, set()),
        ("TEST_WORKFLOW", "X27", APP_V2_JSON, set()),
        ("TEST_WORKFLOW2", "X26", APP_V1_JSON, {_CANNED_MAILBOX1, _CANNED_MAILBOX2}),
        ("TEST_WORKFLOW2", "X26", APP_V2_JSON, {_CANNED_MAILBOX1, _CANNED_MAILBOX2}),
        ("TEST_WORKFLOW_ACK", "X26", APP_V1_JSON, {_CANNED_MAILBOX1}),
        ("TEST_WORKFLOW_ACK", "X26", APP_V2_JSON, {_CANNED_MAILBOX1}),
        ("TEST_WORKFLOW_ACK", "X27", APP_V1_JSON, {_CANNED_MAILBOX3}),
        ("TEST_WORKFLOW_ACK", "X27", APP_V2_JSON, {_CANNED_MAILBOX3}),
        (uuid4().hex, "X27", APP_V1_JSON, set()),
        (uuid4().hex, "X27", APP_V2_JSON, set()),
    ],
)
def test_endpoint_lookup(app: TestClient, workflow_id: str, ods_code: str, accepts: str, expected: list[str]):

    res = app.get(
        f"/messageexchange/endpointlookup/{ods_code}/{workflow_id}",
        headers={Headers.Accept: accepts},
    )

    assert res.status_code == status.HTTP_200_OK
    result = res.json()

    mailboxes = (
        {res["address"] for res in result.get("results", [])}
        if accepts == APP_V1_JSON
        else {res["mailbox_id"] for res in result.get("results", [])}
    )

    assert mailboxes == expected


@pytest.mark.parametrize(
    "workflow_id, accepts, expected",
    [
        ("TEST_WORKFLOW", APP_V1_JSON, {_CANNED_MAILBOX2}),
        ("TEST_WORKFLOW", APP_V2_JSON, {_CANNED_MAILBOX2}),
        ("TEST_WORKFLOW_ACK", APP_V1_JSON, {_CANNED_MAILBOX1, _CANNED_MAILBOX3}),
        ("TEST_WORKFLOW_ACK", APP_V2_JSON, {_CANNED_MAILBOX1, _CANNED_MAILBOX3}),
        ("TEST_WORKFLOW2", APP_V1_JSON, {_CANNED_MAILBOX1, _CANNED_MAILBOX2, _CANNED_MAILBOX3}),
        ("TEST_WORKFLOW2", APP_V2_JSON, {_CANNED_MAILBOX1, _CANNED_MAILBOX2, _CANNED_MAILBOX3}),
        (uuid4().hex, APP_V1_JSON, set()),
        (uuid4().hex, APP_V2_JSON, set()),
    ],
)
def test_workflow_search(app: TestClient, workflow_id: str, accepts: str, expected: list[str]):

    res = app.get(
        f"/messageexchange/workflowsearch/{workflow_id}",
        headers={Headers.Accept: accepts},
    )

    assert res.status_code == status.HTTP_200_OK
    result = res.json()

    mailboxes = {res["mailbox_id"] for res in result.get("results", [])}

    assert mailboxes == expected
