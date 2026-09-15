"""Domain models shared by every agent."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum


class Performative(StrEnum):
    INFORM = "inform"
    CFP = "call-for-proposal"
    PROPOSE = "propose"
    ACCEPT = "accept-proposal"
    REJECT = "reject-proposal"
    COMPLETE = "complete"


class TaskKind(StrEnum):
    IRRIGATE = "irrigate"
    FERTILIZE = "fertilize"
    HARVEST = "harvest"


@dataclass
class Zone:
    id: str
    row: int
    column: int
    moisture: float
    nutrients: float
    temperature: float
    crop_health: float
    maturity: float
    pest_level: float = 0.0

    def clamp(self) -> None:
        for name in ("moisture", "nutrients", "crop_health", "maturity", "pest_level"):
            setattr(self, name, min(100.0, max(0.0, getattr(self, name))))


@dataclass(frozen=True)
class Message:
    sender: str
    recipient: str
    performative: Performative
    conversation_id: str
    payload: dict
    tick: int


@dataclass
class Task:
    id: str
    kind: TaskKind
    zone_id: str
    urgency: float
    quantity: float
    created_at: int
    status: str = "announced"
    contractor: str | None = None
    completed_at: int | None = None
    bids: dict[str, float] = field(default_factory=dict)


@dataclass
class Resources:
    water: float = 650.0
    fertilizer: float = 180.0
    fuel: float = 260.0


@dataclass
class Event:
    tick: int
    kind: str
    zone_id: str | None = None
    magnitude: float = 1.0


@dataclass
class Metrics:
    water_used: float = 0.0
    fertilizer_used: float = 0.0
    fuel_used: float = 0.0
    harvested_yield: float = 0.0
    completed_tasks: int = 0
    failed_tasks: int = 0
    messages: int = 0
    response_times: list[int] = field(default_factory=list)

    def snapshot(self) -> dict:
        result = asdict(self)
        result["average_response_time"] = (
            sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
        )
        return result
