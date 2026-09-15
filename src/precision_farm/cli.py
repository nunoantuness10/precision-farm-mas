"""Run repeatable scenarios from the command line."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .simulation import FarmSimulation, SimulationConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Decentralized precision-farm simulator")
    parser.add_argument(
        "--scenario", choices=["normal", "drought", "pest", "failure", "mixed"], default="mixed"
    )
    parser.add_argument("--ticks", type=int, default=60)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="results/latest.json")
    args = parser.parse_args()
    result = FarmSimulation(
        SimulationConfig(ticks=args.ticks, seed=args.seed, scenario=args.scenario)
    ).run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    metrics = result["metrics"]
    summary = {
        "scenario": args.scenario,
        "completed_tasks": metrics["completed_tasks"],
        "water_used": metrics["water_used"],
        "fertilizer_used": metrics["fertilizer_used"],
        "fuel_used": metrics["fuel_used"],
        "harvested_yield": metrics["harvested_yield"],
        "messages": metrics["messages"],
        "average_response_time": metrics["average_response_time"],
        "final_health": result["history"][-1]["average_crop_health"],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
