"""CLI entry for the live simulator process (separate from Streamlit)."""

import argparse
import sys

from gridpulse.config.paths import resolve_events_path
from gridpulse.simulator.core import DEFAULT_CHANNELS, LiveSimulator


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gridpulse-simulate",
        description=(
            "Continuous Grid Pulse data-simulator. Appends pipeline JSONL ticks "
            "to the fixed events path. Run in a separate terminal from Streamlit."
        ),
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between ticks (default: 1.0)",
    )
    parser.add_argument(
        "--full-coverage",
        action="store_true",
        help="Report every configured channel each tick (default: sparse subset)",
    )
    parser.add_argument(
        "--inject-rate",
        type=float,
        default=0.05,
        help="Per-tick probability of injecting a measurement spike (default: 0.05)",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=None,
        help="Stop after N ticks (default: run forever)",
    )
    parser.add_argument("--network", default="case14")
    parser.add_argument(
        "--history",
        type=int,
        default=30,
        help="Quiet history warmup ticks for detectors (default: 30)",
    )
    args = parser.parse_args(argv)

    path = resolve_events_path()
    print(
        f"gridpulse-simulate → {path} "
        f"(interval={args.interval}s, full_coverage={args.full_coverage}, "
        f"inject_rate={args.inject_rate}, seed={args.seed})",
        file=sys.stderr,
    )
    sim = LiveSimulator(
        channels=list(DEFAULT_CHANNELS),
        seed=args.seed,
        full_coverage=args.full_coverage,
        inject_rate=args.inject_rate,
        history_warmup=args.history,
        network=args.network,
    )
    try:
        sim.run(path, interval=args.interval, max_ticks=args.max_ticks)
    except KeyboardInterrupt:
        print("\nstopped", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
