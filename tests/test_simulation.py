from precision_farm.models import Performative
from precision_farm.simulation import FarmSimulation, SimulationConfig


def run(scenario="mixed", **overrides):
    return FarmSimulation(SimulationConfig(scenario=scenario, ticks=60, seed=42, **overrides)).run()


def test_run_is_deterministic():
    first = run()
    second = run()
    assert first["metrics"] == second["metrics"]
    assert first["zones"] == second["zones"]


def test_contract_net_lifecycle_is_visible():
    result = run("drought")
    actions = {message["performative"] for message in result["message_log"]}
    assert Performative.CFP in actions
    assert Performative.PROPOSE in actions
    assert Performative.ACCEPT in actions
    assert Performative.COMPLETE in actions
    assert result["metrics"]["completed_tasks"] > 0


def test_resource_use_never_exceeds_initial_budget():
    result = run()
    assert result["metrics"]["water_used"] <= 650
    assert result["metrics"]["fertilizer_used"] <= 180
    assert result["metrics"]["fuel_used"] <= 260


def test_failure_and_repair_change_agent_availability():
    result = run("failure")
    active = {row["tick"]: row["active_agents"] for row in result["history"]}
    assert active[18] < active[17]
    assert active[30] == active[17]


def test_zones_remain_in_physical_ranges():
    result = run("mixed")
    for zone in result["zones"]:
        for key in ("moisture", "nutrients", "crop_health", "maturity", "pest_level"):
            assert 0 <= zone[key] <= 100
