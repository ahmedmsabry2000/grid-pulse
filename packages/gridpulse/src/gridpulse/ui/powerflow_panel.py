"""Re-run gate/PF/detectors on the latest JSONL tick for UI panels."""

from datetime import datetime
from typing import Any

from gridpulse.config import DEFAULT_SETTINGS, Settings
from gridpulse.pipeline import run_tick
from gridpulse.telemetry import HistoricalStore, Measurement, QualityFlag


def measurements_from_event(event: dict[str, Any]) -> list[Measurement]:
    out: list[Measurement] = []
    for m in event.get("measurements", []):
        out.append(
            Measurement(
                timestamp=datetime.fromisoformat(m["timestamp"]),
                signal_id=m["signal_id"],
                value=m["value"],
                quality=QualityFlag(m["quality"]),
            )
        )
    return out


def history_from_events(events: list[dict[str, Any]], *, exclude_last: bool = True) -> HistoricalStore:
    ticks = events[:-1] if exclude_last and events else events
    store = HistoricalStore()
    for ev in ticks:
        store.extend(measurements_from_event(ev))
    return store


def run_powerflow_on_latest(
    events: list[dict[str, Any]],
    *,
    network: str = "case14",
    settings: Settings = DEFAULT_SETTINGS,
) -> dict[str, Any]:
    """Load the latest tick from the stream and re-run the pipeline tick.

    Returns a structured panel payload with gate, powerflow, rating exceedances,
    and ensemble (plus other) anomalies kept as separate lists.
    """
    if not events:
        return {
            "ok": False,
            "error": "no events in stream",
            "gate": None,
            "powerflow": None,
            "rating_exceedances": [],
            "ensemble_anomalies": [],
            "other_anomalies": [],
            "record": None,
        }
    latest = events[-1]
    sample = measurements_from_event(latest)
    previous = measurements_from_event(events[-2]) if len(events) >= 2 else None
    store = history_from_events(events, exclude_last=True)
    rec = run_tick(
        sample,
        history=store,
        network=network,
        tick_index=int(latest.get("tick_index", len(events) - 1)),
        previous=previous,
        settings=settings,
    )
    anomalies = list(rec.get("anomalies", []))
    rating = [a for a in anomalies if a.get("type") == "rating_exceedance"]
    ensemble = [a for a in anomalies if a.get("type") == "measurement_ensemble"]
    other = [
        a
        for a in anomalies
        if a.get("type") not in {"rating_exceedance", "measurement_ensemble"}
    ]
    return {
        "ok": True,
        "error": None,
        "gate": rec.get("gate"),
        "powerflow": rec.get("powerflow"),
        "rating_exceedances": rating,
        "ensemble_anomalies": ensemble,
        "other_anomalies": other,
        "record": rec,
    }
