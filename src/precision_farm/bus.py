"""In-memory peer-to-peer transport with explicit mailboxes."""

from __future__ import annotations

from collections import defaultdict, deque

from .models import Message


class MessageBus:
    def __init__(self) -> None:
        self.mailboxes: dict[str, deque[Message]] = defaultdict(deque)
        self.log: list[Message] = []

    def send(self, message: Message) -> None:
        self.mailboxes[message.recipient].append(message)
        self.log.append(message)

    def receive(self, recipient: str) -> list[Message]:
        messages = list(self.mailboxes[recipient])
        self.mailboxes[recipient].clear()
        return messages
