from dataclasses import asdict
from uuid import uuid4

from ..models.message import Message, MessageMetadata, MessageParty
from ..store.serialisation import deserialise_model, serialise_model


def test_serialise_deserialise_message():

    message = Message(
        message_id=uuid4().hex,
        metadata=MessageMetadata(local_id=uuid4().hex),
        sender=MessageParty(mailbox_id=uuid4().hex),
        recipient=MessageParty(mailbox_id=uuid4().hex),
    )

    serialised = serialise_model(message)

    assert serialised

    deserialised = deserialise_model(serialised, Message)

    assert asdict(deserialised) == asdict(message)
