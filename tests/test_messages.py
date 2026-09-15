from precision_farm.bus import MessageBus
from precision_farm.models import Message, Performative


def test_mailboxes_are_recipient_specific_and_drained():
    bus = MessageBus()
    message = Message("sensor", "drone", Performative.INFORM, "reading-1", {"moisture": 20}, 1)
    bus.send(message)
    assert bus.receive("other") == []
    assert bus.receive("drone") == [message]
    assert bus.receive("drone") == []
