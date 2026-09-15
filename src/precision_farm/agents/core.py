"""Autonomous agents and Contract Net behaviours."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from uuid import uuid4

from ..bus import MessageBus
from ..models import Message, Metrics, Performative, Task, TaskKind, Zone


@dataclass
class Agent:
    name: str
    bus: MessageBus
    metrics: Metrics
    online: bool = True

    def send(
        self,
        recipient: str,
        performative: Performative,
        conversation_id: str,
        payload: dict,
        tick: int,
    ) -> None:
        self.bus.send(Message(self.name, recipient, performative, conversation_id, payload, tick))
        self.metrics.messages += 1

    def inbox(self) -> list[Message]:
        return self.bus.receive(self.name)


@dataclass
class SensorAgent(Agent):
    zone_ids: list[str] = field(default_factory=list)
    subscribers: list[str] = field(default_factory=list)

    def step(self, tick: int, zones: dict[str, Zone]) -> None:
        if not self.online:
            return
        for zone_id in self.zone_ids:
            zone = zones[zone_id]
            payload = {
                "zone_id": zone_id,
                "moisture": zone.moisture,
                "nutrients": zone.nutrients,
                "temperature": zone.temperature,
                "maturity": zone.maturity,
                "row": zone.row,
                "column": zone.column,
            }
            for recipient in self.subscribers:
                self.send(
                    recipient, Performative.INFORM, f"reading-{tick}-{zone_id}", payload, tick
                )


@dataclass
class DroneAgent(Agent):
    zone_ids: list[str] = field(default_factory=list)
    contractors: dict[TaskKind, list[str]] = field(default_factory=dict)
    open_tasks: dict[str, Task] = field(default_factory=dict)
    known_task_keys: set[tuple[TaskKind, str]] = field(default_factory=set)

    def announce(
        self, kind: TaskKind, zone: Zone, urgency: float, quantity: float, tick: int
    ) -> None:
        key = (kind, zone.id)
        if key in self.known_task_keys:
            return
        task_id = f"{kind.value}-{uuid4().hex[:8]}"
        task = Task(task_id, kind, zone.id, urgency, quantity, tick)
        self.open_tasks[task_id] = task
        self.known_task_keys.add(key)
        payload = {
            "kind": kind.value,
            "zone_id": zone.id,
            "urgency": urgency,
            "quantity": quantity,
            "row": zone.row,
            "column": zone.column,
        }
        for contractor in self.contractors[kind]:
            self.send(contractor, Performative.CFP, task_id, payload, tick)

    def monitor(self, tick: int, zones: dict[str, Zone]) -> None:
        if not self.online:
            return
        for zone_id in self.zone_ids:
            zone = zones[zone_id]
            if zone.pest_level >= 35 or zone.nutrients < 35:
                self.announce(
                    TaskKind.FERTILIZE, zone, max(zone.pest_level, 35 - zone.nutrients), 12, tick
                )
            if zone.maturity >= 92:
                self.announce(TaskKind.HARVEST, zone, zone.maturity, 1, tick)

    def process_messages(self, tick: int) -> None:
        for message in self.inbox():
            if message.performative == Performative.INFORM:
                if message.payload["zone_id"] not in self.zone_ids:
                    continue
                moisture = message.payload["moisture"]
                if moisture < 38:
                    # The reading contains location-free observations; the drone owns
                    # its local map and starts the negotiation for its own sector.
                    zone_stub = Zone(
                        message.payload["zone_id"],
                        message.payload["row"],
                        message.payload["column"],
                        moisture,
                        0,
                        0,
                        0,
                        0,
                    )
                    self.announce(TaskKind.IRRIGATE, zone_stub, 38 - moisture, 18, tick)
            elif message.performative == Performative.PROPOSE:
                task = self.open_tasks.get(message.conversation_id)
                if task and task.status == "announced":
                    task.bids[message.sender] = float(message.payload["cost"])
            elif message.performative == Performative.COMPLETE:
                task = self.open_tasks.get(message.conversation_id)
                if task:
                    task.status = "completed"
                    task.completed_at = tick
                    self.known_task_keys.discard((task.kind, task.zone_id))
                    self.metrics.completed_tasks += 1
                    # Negotiation is completed within one simulated scheduling cycle.
                    self.metrics.response_times.append(tick - task.created_at + 1)

    def award_contracts(self, tick: int) -> None:
        for task in self.open_tasks.values():
            if task.status != "announced" or not task.bids:
                continue
            winner = min(task.bids, key=task.bids.get)
            task.contractor = winner
            task.status = "awarded"
            for bidder in task.bids:
                performative = Performative.ACCEPT if bidder == winner else Performative.REJECT
                self.send(bidder, performative, task.id, {"zone_id": task.zone_id}, tick)


@dataclass
class ServiceAgent(Agent):
    capability: TaskKind = TaskKind.IRRIGATE
    row: int = 0
    column: int = 0
    stock: float = 0.0
    fuel: float = 100.0
    pending: dict[str, dict] = field(default_factory=dict)

    def process_messages(self, tick: int, zones: dict[str, Zone]) -> None:
        for message in self.inbox():
            if not self.online:
                continue
            if message.performative == Performative.CFP:
                payload = message.payload
                if payload["kind"] != self.capability.value:
                    continue
                quantity = float(payload["quantity"])
                distance = hypot(payload["row"] - self.row, payload["column"] - self.column)
                if self.stock >= quantity and self.fuel >= distance * 0.4:
                    cost = distance + quantity / max(self.stock, 1) - payload["urgency"] * 0.02
                    self.pending[message.conversation_id] = {**payload, "requester": message.sender}
                    self.send(
                        message.sender,
                        Performative.PROPOSE,
                        message.conversation_id,
                        {"cost": cost},
                        tick,
                    )
            elif message.performative == Performative.REJECT:
                self.pending.pop(message.conversation_id, None)
            elif message.performative == Performative.ACCEPT:
                proposal = self.pending.pop(message.conversation_id, None)
                if proposal:
                    self.execute(message.conversation_id, proposal, tick, zones)

    def execute(self, task_id: str, proposal: dict, tick: int, zones: dict[str, Zone]) -> None:
        zone = zones[proposal["zone_id"]]
        quantity = min(float(proposal["quantity"]), self.stock)
        distance = hypot(zone.row - self.row, zone.column - self.column)
        fuel_used = min(self.fuel, distance * 0.4 + 0.2)
        self.fuel -= fuel_used
        self.metrics.fuel_used += fuel_used
        if self.capability == TaskKind.IRRIGATE:
            self.stock -= quantity
            zone.moisture += quantity * 1.8
            self.metrics.water_used += quantity
        elif self.capability == TaskKind.FERTILIZE:
            self.stock -= quantity
            zone.nutrients += quantity * 1.4
            zone.pest_level -= quantity * 2.0
            self.metrics.fertilizer_used += quantity
        else:
            self.stock -= quantity
            harvested = zone.maturity * zone.crop_health / 100
            self.metrics.harvested_yield += harvested
            zone.maturity = 5
        zone.clamp()
        self.row, self.column = zone.row, zone.column
        self.send(proposal["requester"], Performative.COMPLETE, task_id, {}, tick)
