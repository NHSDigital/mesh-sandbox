from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4

import pytest

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
    assert deserialised
    assert asdict(deserialised) == asdict(message)


@dataclass
class _OptionalTimestamp:
    timestamp: Optional[datetime] = None


@dataclass
class _PipeUnionTimestamp:
    timestamp: datetime | None = None


@pytest.mark.parametrize("model_type", [_OptionalTimestamp, _PipeUnionTimestamp])
def test_deserialise_optional_datetime(model_type):
    timestamp = datetime(2026, 11, 10, 17, 22, 6, 123456)

    serialised = serialise_model(model_type(timestamp=timestamp))
    assert serialised == {"timestamp": timestamp.isoformat()}

    deserialised = deserialise_model(serialised, model_type)
    assert deserialised
    assert deserialised.timestamp == timestamp
