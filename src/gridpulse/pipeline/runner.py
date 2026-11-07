"""Tick / batch orchestration → structured events."""

import json
from pathlib import Path
from typing import Any, TextIO

from gridpulse.anomaly import detect_measurement_anomalies, detect_rating_exceedances
from gridpulse.config import DEFAULT_SETTINGS, Settings
from gridpulse.network import load_network
from gridpulse.powerflow import run_powerflow
from gridpulse.quality import GateDecision, PowerflowGate
from gridpulse.telemetry import HistoricalStore, Measurement


def _measurement_dict(m: Measurement) -> dict[str, Any]:
    return {
        "timestamp": m.timestamp.isoformat(),
        "signal_id": m.signal_id,
        "value": m.value,
        "quality": m.quality.value,
    }


def _anomaly_dict(a: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": a.type.value,
        "signal_id": a.signal_id,
        "timestamp": a.timestamp.isoformat(),
        "value": a.value,
        "score": a.score if a.score != float("inf") else "inf",
        "detail": a.detail,
    }
    if a.quantity is not None:
        payload["quantity"] = a.quantity
    if a.limit is not None:
        payload["limit"] = a.limit
    if a.margin is not None:
        payload["margin"] = a.margin
    return payload


def run_tick(
    sample: list[Measurement],
    *,
    history_ticks: list[list[Measurement]] | None = None,
    history: HistoricalStore | None = None,
    network: str = "case14",
    tick_index: int = 0,
    previous: list[Measurement] | None = None,
    settings: Settings = DEFAULT_SETTINGS,
    net: Any | None = None,
) -> dict[str, Any]:
    """Run one discrete tick: gate → optional PF → anomalies (measurement + rating)."""
    store = history or HistoricalStore.from_ticks(history_ticks or [])
    working_net = net if net is not None else load_network(network)
    gate = PowerflowGate().decide(sample, previous=previous, net=working_net)

    pf_payload: dict[str, Any] = {"ran": False, "converged": None, "error": None}
    rating_events: list[Any] = []
    if gate.action is GateDecision.RUN:
        result = run_powerflow(working_net, sample, gate=gate)
        pf_payload = {
            "ran": True,
            "converged": result.converged,
            "error": result.error,
        }
        # Rating exceedance is independent of historical anomaly scoring.
        if result.converged and result.net is not None:
            ts = sample[0].timestamp if sample else None
            if ts is not None:
                rating_events = detect_rating_exceedances(result.net, timestamp=ts)

    # Historical measurement anomalies — never suppressed by rating outcomes.
    anomalies = detect_measurement_anomalies(
        sample,
        store,
        z_threshold=settings.z_threshold,
        spike_threshold=settings.spike_threshold,
    )
    anomalies = list(anomalies) + list(rating_events)

    return {
        "tick_index": tick_index,
        "gate": {
            "action": gate.action.value,
            "reason": None if gate.reason is None else gate.reason.value,
        },
        "powerflow": pf_payload,
        "anomalies": [_anomaly_dict(a) for a in anomalies],
        "measurements": [_measurement_dict(m) for m in sample],
    }


def run_batch(
    ticks: list[list[Measurement]],
    *,
    history_ticks: list[list[Measurement]] | None = None,
    network: str = "case14",
    jsonl_path: str | Path | None = None,
    stdout: TextIO | None = None,
    settings: Settings = DEFAULT_SETTINGS,
) -> list[dict[str, Any]]:
    """Run discrete offline batch; write JSONL + optional stdout mirror."""
    store = HistoricalStore.from_ticks(history_ticks or [])
    net = load_network(network)
    records: list[dict[str, Any]] = []
    previous: list[Measurement] | None = None
    sink = open(jsonl_path, "w", encoding="utf-8") if jsonl_path else None
    try:
        for i, sample in enumerate(ticks):
            rec = run_tick(
                sample,
                history=store,
                network=network,
                tick_index=i,
                previous=previous,
                settings=settings,
                net=net,
            )
            records.append(rec)
            line = json.dumps(rec, sort_keys=True)
            if sink:
                sink.write(line + "\n")
            if stdout is not None:
                stdout.write(line + "\n")
            store.extend(sample)
            previous = sample
    finally:
        if sink:
            sink.close()
    return records
