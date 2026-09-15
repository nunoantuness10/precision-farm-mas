"""Deterministic environment and agent scheduler (not a central decision-maker)."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass

from .agents import DroneAgent, SensorAgent, ServiceAgent
from .bus import MessageBus
from .models import Event, Metrics, Resources, TaskKind, Zone


@dataclass(frozen=True)
class SimulationConfig:
    rows: int = 4
    columns: int = 4
    ticks: int = 60
    seed: int = 42
    scenario: str = "mixed"
    water: float = 650
    fertilizer: float = 180
    fuel: float = 260


class FarmSimulation:
    """A world clock plus autonomous agents; allocation decisions stay with agents."""

    def __init__(self, config: SimulationConfig | None = None) -> None:
        self.config = config or SimulationConfig()
        config = self.config
        self.random = random.Random(config.seed)
        self.bus = MessageBus()
        self.metrics = Metrics()
        self.resources = Resources(config.water, config.fertilizer, config.fuel)
        self.zones = self._make_zones()
        self.events = self._make_events()
        self.tick = 0
        zone_ids = list(self.zones)
        split = len(zone_ids) // 2
        irrigation_names = ["irrigation-west", "irrigation-east"]
        fertilizer_names = ["logistics-fertilizer"]
        harvester_names = ["harvester-alpha"]
        contractors = {
            TaskKind.IRRIGATE: irrigation_names,
            TaskKind.FERTILIZE: fertilizer_names,
            TaskKind.HARVEST: harvester_names,
        }
        self.drones = [
            DroneAgent(
                "drone-north",
                self.bus,
                self.metrics,
                zone_ids=zone_ids[:split],
                contractors=contractors,
            ),
            DroneAgent(
                "drone-south",
                self.bus,
                self.metrics,
                zone_ids=zone_ids[split:],
                contractors=contractors,
            ),
        ]
        subscribers = [agent.name for agent in self.drones]
        self.sensors = [
            SensorAgent(
                f"sensor-{index}", self.bus, self.metrics, zone_ids=group, subscribers=subscribers
            )
            for index, group in enumerate((zone_ids[::2], zone_ids[1::2]), 1)
        ]
        self.services = [
            ServiceAgent(
                irrigation_names[0],
                self.bus,
                self.metrics,
                capability=TaskKind.IRRIGATE,
                row=0,
                column=0,
                stock=config.water / 2,
                fuel=config.fuel / 4,
            ),
            ServiceAgent(
                irrigation_names[1],
                self.bus,
                self.metrics,
                capability=TaskKind.IRRIGATE,
                row=config.rows - 1,
                column=config.columns - 1,
                stock=config.water / 2,
                fuel=config.fuel / 4,
            ),
            ServiceAgent(
                fertilizer_names[0],
                self.bus,
                self.metrics,
                capability=TaskKind.FERTILIZE,
                row=0,
                column=config.columns - 1,
                stock=config.fertilizer,
                fuel=config.fuel / 4,
            ),
            ServiceAgent(
                harvester_names[0],
                self.bus,
                self.metrics,
                capability=TaskKind.HARVEST,
                row=config.rows - 1,
                column=0,
                stock=100,
                fuel=config.fuel / 4,
            ),
        ]
        self.history: list[dict] = []

    def _make_zones(self) -> dict[str, Zone]:
        zones = {}
        for row in range(self.config.rows):
            for column in range(self.config.columns):
                zone_id = f"Z{row + 1}{column + 1}"
                zones[zone_id] = Zone(
                    zone_id,
                    row,
                    column,
                    self.random.uniform(42, 72),
                    self.random.uniform(45, 75),
                    self.random.uniform(17, 27),
                    self.random.uniform(70, 95),
                    self.random.uniform(45, 82),
                )
        return zones

    def _make_events(self) -> list[Event]:
        if self.config.scenario == "normal":
            return []
        if self.config.scenario == "drought":
            return [Event(12, "drought", magnitude=1.8)]
        if self.config.scenario == "pest":
            return [Event(15, "pest", "Z22", 1.6)]
        if self.config.scenario == "failure":
            return [
                Event(18, "failure", "irrigation-west", 1),
                Event(30, "repair", "irrigation-west", 1),
            ]
        return [
            Event(10, "drought", magnitude=1.5),
            Event(18, "pest", "Z22", 1.4),
            Event(25, "failure", "irrigation-west"),
            Event(36, "repair", "irrigation-west"),
            Event(42, "rain", magnitude=1.2),
        ]

    def _environment(self) -> None:
        drought = 1.0
        for event in [item for item in self.events if item.tick == self.tick]:
            if event.kind == "pest" and event.zone_id in self.zones:
                self.zones[event.zone_id].pest_level += 35 * event.magnitude
            elif event.kind in {"failure", "repair"}:
                for agent in [*self.drones, *self.sensors, *self.services]:
                    if agent.name == event.zone_id:
                        agent.online = event.kind == "repair"
            elif event.kind == "rain":
                for zone in self.zones.values():
                    zone.moisture += 12 * event.magnitude
        if any(event.kind == "drought" and event.tick <= self.tick for event in self.events):
            drought = 1.65
        for zone in self.zones.values():
            zone.moisture -= self.random.uniform(0.7, 1.3) * drought
            zone.nutrients -= self.random.uniform(0.12, 0.3)
            zone.temperature += self.random.uniform(-0.5, 0.5)
            zone.maturity += max(0.1, zone.crop_health / 180)
            zone.crop_health += (zone.moisture - 40) * 0.015 - zone.pest_level * 0.025
            zone.pest_level *= 0.985
            zone.clamp()

    def step(self) -> dict:
        self._environment()
        for sensor in self.sensors:
            sensor.step(self.tick, self.zones)
        for drone in self.drones:
            drone.monitor(self.tick, self.zones)
            drone.process_messages(self.tick)
        for service in self.services:
            service.process_messages(self.tick, self.zones)
        for drone in self.drones:
            drone.process_messages(self.tick)
            drone.award_contracts(self.tick)
        for service in self.services:
            service.process_messages(self.tick, self.zones)
        for drone in self.drones:
            drone.process_messages(self.tick)
        snapshot = self.snapshot()
        self.history.append(snapshot)
        self.tick += 1
        return snapshot

    def snapshot(self) -> dict:
        active = sum(agent.online for agent in [*self.drones, *self.sensors, *self.services])
        zone_values = list(self.zones.values())
        return {
            "tick": self.tick,
            "average_crop_health": sum(zone.crop_health for zone in zone_values) / len(zone_values),
            "average_moisture": sum(zone.moisture for zone in zone_values) / len(zone_values),
            "average_nutrients": sum(zone.nutrients for zone in zone_values) / len(zone_values),
            "active_agents": active,
            **self.metrics.snapshot(),
        }

    def run(self) -> dict:
        for _ in range(self.config.ticks):
            self.step()
        return self.result()

    def result(self) -> dict:
        tasks = [asdict(task) for drone in self.drones for task in drone.open_tasks.values()]
        metrics = self.metrics.snapshot()
        metrics["failed_tasks"] = sum(task["status"] != "completed" for task in tasks)
        return {
            "config": asdict(self.config),
            "metrics": metrics,
            "zones": [asdict(zone) for zone in self.zones.values()],
            "tasks": tasks,
            "history": self.history,
            "events": [asdict(event) for event in self.events],
            "message_log": [asdict(message) for message in self.bus.log],
        }
