"""CLI entry: discrete batch demo with optional fault injection."""

import argparse
import sys
from pathlib import Path

from gridpulse.pipeline.runner import run_batch
from gridpulse.telemetry import FaultSpec, QualityFlag, SyntheticTelemetryGenerator


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gridpulse", description="Grid Pulse batch runner")
    parser.add_argument("--ticks", type=int, default=20)
    parser.add_argument("--history", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--network", default="case14")
    parser.add_argument("--jsonl", type=Path, default=Path("events.jsonl"))
    parser.add_argument("--inject-faults", action="store_true", help="Inject demo measurement faults")
    args = parser.parse_args(argv)

    signals = ["bus_1_vm_pu", "bus_2_vm_pu", "bus_3_vm_pu"]
    faults: list[FaultSpec] = []
    if args.inject_faults:
        faults = [
            FaultSpec(tick_index=max(0, args.ticks // 3), signal_id="bus_1_vm_pu", value=None, quality=QualityFlag.MISSING),
            FaultSpec(tick_index=max(0, 2 * args.ticks // 3), signal_id="bus_2_vm_pu", value=1.14),
        ]

    history = SyntheticTelemetryGenerator(
        signals=signals, seed=args.seed, noise_std=0.002, base_value=1.0
    ).generate_ticks(n=args.history)
    ticks = SyntheticTelemetryGenerator(
        signals=signals, seed=args.seed + 1, noise_std=0.002, base_value=1.0, faults=faults
    ).generate_ticks(n=args.ticks)

    run_batch(
        ticks=ticks,
        history_ticks=history,
        network=args.network,
        jsonl_path=args.jsonl,
        stdout=sys.stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
