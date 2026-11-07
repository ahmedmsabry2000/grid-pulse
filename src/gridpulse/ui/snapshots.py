"""Immutable powerflow snapshot pages frozen on each Run powerflow click."""

import copy
from typing import Any


def freeze_snapshot(
    events: list[dict[str, Any]],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Deep-copy stream events + PF panel payload into an immutable snapshot.

    Live JSONL appends must not mutate the returned structure.
    """
    frozen_events = copy.deepcopy(events)
    tick_start = frozen_events[0]["tick_index"] if frozen_events else None
    tick_end = frozen_events[-1]["tick_index"] if frozen_events else None
    return {
        "tick_start": tick_start,
        "tick_end": tick_end,
        "n_ticks": len(frozen_events),
        "events": frozen_events,
        "result": copy.deepcopy(result),
    }


def append_snapshot(
    snapshots: list[dict[str, Any]],
    snapshot: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    """Append a snapshot and return (list, index of latest)."""
    snapshots.append(snapshot)
    return snapshots, len(snapshots) - 1
