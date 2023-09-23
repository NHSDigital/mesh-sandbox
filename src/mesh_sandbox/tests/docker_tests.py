from uuid import uuid4

from mesh_client import MeshClient

_CANNED_MAILBOX1 = "X26ABC1"
_CANNED_MAILBOX2 = "X26ABC2"
_SHARED_KEY = b"TestKey"
_PASSWORD = "password"


def test_send_receive_chunked_message():
    sender_mailbox_id = _CANNED_MAILBOX1
    recipient_mailbox_id = _CANNED_MAILBOX2
    workflow_id = uuid4().hex

    base_uri = "https://localhost:8700"

    with MeshClient(
        url=base_uri,
        mailbox=sender_mailbox_id,
        password=_PASSWORD,
        shared_key=_SHARED_KEY,
        max_chunk_size=100,
        verify=False,
    ) as sender:
        sent_payload = b"a" * 1000

        message_id = sender.send_message(_CANNED_MAILBOX2, sent_payload, workflow_id=workflow_id, subject="change me")

        assert message_id

        with MeshClient(
            url=base_uri, mailbox=recipient_mailbox_id, password=_PASSWORD, shared_key=_SHARED_KEY, verify=False
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

            # test that plugin is loaded and is able to edit the message ( though this wouldn't be saved in file mode )
            assert message.subject == "plugin message from file"  # pylint: disable=no-member
