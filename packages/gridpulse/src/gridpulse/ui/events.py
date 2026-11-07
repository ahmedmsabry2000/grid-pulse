"""Load Stage 6 JSONL events for the time-series UI."""

import json
from pathlib import Path
from typing import Any

import pandas as pd


def load_events(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def available_signals(events: list[dict[str, Any]]) -> list[str]:
    ids: set[str] = set()
    for ev in events:
        for m in ev.get("measurements", []):
            ids.add(m["signal_id"])
    return sorted(ids)


def series_frame(events: list[dict[str, Any]], signal_id: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for ev in events:
        meas = next((m for m in ev.get("measurements", []) if m["signal_id"] == signal_id), None)
        # Signal-scoped anomalies plus tick-level rating exceedance markers
        # (object ids like line:0 do not match measurement signal ids).
        anomaly_hits = [
            a
            for a in ev.get("anomalies", [])
            if a.get("signal_id") == signal_id or a.get("type") == "rating_exceedance"
        ]
        rows.append(
            {
                "tick_index": ev["tick_index"],
                "timestamp": meas["timestamp"] if meas else None,
                "value": meas["value"] if meas else None,
                "is_skip": ev.get("gate", {}).get("action") == "skip",
                "skip_reason": ev.get("gate", {}).get("reason"),
                "is_anomaly": bool(anomaly_hits),
                "anomaly_types": ",".join(a["type"] for a in anomaly_hits),
            }
        )
    return pd.DataFrame(rows)
