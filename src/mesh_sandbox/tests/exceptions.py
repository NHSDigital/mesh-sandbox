from uuid import uuid4

from ..common import constants
from ..common.exceptions import try_parse_error


def test_parse_simple_error():

    res = try_parse_error(constants.ERROR_NO_MAILBOX_MATCHES)
    assert res
    assert res["errorCode"] == "EPL-151"
    assert res["errorEvent"] == "SEND"
    assert res["errorDescription"] == constants.ERROR_NO_MAILBOX_MATCHES


def test_parse_simple_error_with_message_id():
    message_id = uuid4().hex
    res = try_parse_error(constants.ERROR_NO_MAILBOX_MATCHES, message_id=message_id)
    assert res
    assert res["errorCode"] == "EPL-151"
    assert res["errorEvent"] == "SEND"
    assert res["errorDescription"] == constants.ERROR_NO_MAILBOX_MATCHES
    assert res["messageID"] == message_id
