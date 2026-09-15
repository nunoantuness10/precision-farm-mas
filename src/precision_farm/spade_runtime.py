"""Optional SPADE/XMPP transport for the same domain protocol.

The default in-memory transport makes demonstrations reproducible without accounts.
This module provides a real SPADE Agent and CyclicBehaviour for deployments where one
XMPP JID and password are available for each farm agent.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from .models import Message as DomainMessage
from .models import Performative

try:
    from spade.agent import Agent as SpadeAgent
    from spade.behaviour import CyclicBehaviour
    from spade.message import Message as SpadeMessage
except ImportError:
    SpadeAgent = object
    CyclicBehaviour = object
    SpadeMessage = None


def require_spade() -> None:
    if SpadeMessage is None:
        raise RuntimeError("Install the SPADE integration with: pip install -e '.[spade]'")


def to_spade_message(domain_message: DomainMessage, recipient_jid: str | None = None):
    """Convert a transport-neutral domain message into a SPADE message."""
    require_spade()
    message = SpadeMessage(to=recipient_jid or domain_message.recipient)
    message.set_metadata("performative", domain_message.performative.value)
    message.set_metadata("conversation-id", domain_message.conversation_id)
    message.set_metadata("sender-name", domain_message.sender)
    message.set_metadata("tick", str(domain_message.tick))
    message.body = json.dumps(domain_message.payload)
    return message


def from_spade_message(message, recipient_name: str) -> DomainMessage:
    """Convert an incoming SPADE message back into the domain model."""
    return DomainMessage(
        sender=message.get_metadata("sender-name") or str(message.sender),
        recipient=recipient_name,
        performative=Performative(message.get_metadata("performative")),
        conversation_id=message.get_metadata("conversation-id"),
        payload=json.loads(message.body or "{}"),
        tick=int(message.get_metadata("tick") or 0),
    )


if SpadeMessage is not None:

    class DomainInboxBehaviour(CyclicBehaviour):
        """Receive XMPP messages and delegate decisions to domain-agent logic."""

        async def run(self) -> None:
            incoming = await self.receive(timeout=1)
            if incoming:
                domain_message = from_spade_message(incoming, self.agent.domain_name)
                await self.agent.domain_handler(domain_message)

    class SpadeFarmAgent(SpadeAgent):
        """Thin SPADE shell; decision logic remains transport-independent."""

        def __init__(
            self,
            jid: str,
            password: str,
            domain_name: str,
            directory: dict[str, str],
            handler: Callable[[DomainMessage], Awaitable[None]],
        ) -> None:
            super().__init__(jid, password)
            self.domain_name = domain_name
            self.directory = directory
            self.domain_handler = handler

        async def setup(self) -> None:
            self.add_behaviour(DomainInboxBehaviour())

        async def send_domain(self, message: DomainMessage) -> None:
            await self.send(to_spade_message(message, self.directory[message.recipient]))

else:

    class SpadeFarmAgent:  # pragma: no cover
        def __init__(self, *args, **kwargs) -> None:
            require_spade()
