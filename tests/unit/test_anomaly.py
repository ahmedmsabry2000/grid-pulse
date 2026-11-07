"""Stage 5: measurement-fault anomaly detectors."""

from datetime import datetime, timedelta, timezone

import pytest

from gridpulse.anomaly import (
    AnomalyEvent,
    AnomalyType,
    detect_measurement_anomalies,
)
from gridpulse.telemetry import HistoricalStore, Measurement, QualityFlag, SyntheticTelemetryGenerator, FaultSpec


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _hist(values: list[float], signal_id: str = "bus_1_vm_pu") -> HistoricalStore:
    store = HistoricalStore()
    for i, v in enumerate(values):
        store.append(
            Measurement(
                timestamp=TS + timedelta(minutes=i),
                signal_id=signal_id,
                value=v,
                quality=QualityFlag.GOOD,
            )
        )
    return store


def test_anomaly_type_reserves_pf_residual() -> None:
    assert AnomalyType.MEASUREMENT_SPIKE.value == "measurement_spike"
    assert AnomalyType.MEASUREMENT_ZSCORE.value == "measurement_zscore"
    assert AnomalyType.PF_RESIDUAL.value == "pf_residual"
    # Reserved only — no residual detector implementation in MVP


def test_seeded_spike_fires() -> None:
    signals = ["bus_1_vm_pu"]
    # Build calm history then inject spike within quality range but anomalous vs history
    hist_ticks = SyntheticTelemetryGenerator(
        signals=signals, seed=1, noise_std=0.002, base_value=1.0
    ).generate_ticks(n=30)
    store = HistoricalStore.from_ticks(hist_ticks)
    sample = [
        Measurement(TS + timedelta(minutes=30), "bus_1_vm_pu", 1.12, QualityFlag.GOOD),
    ]
    events = detect_measurement_anomalies(sample, store, z_threshold=3.0, spike_threshold=0.05)
    assert any(e.type is AnomalyType.MEASUREMENT_SPIKE for e in events) or any(
        e.type is AnomalyType.MEASUREMENT_ZSCORE for e in events
    )
    assert all(e.type is not AnomalyType.PF_RESIDUAL for e in events)


def test_clean_noise_under_threshold() -> None:
    signals = ["bus_1_vm_pu"]
    gen = SyntheticTelemetryGenerator(signals=signals, seed=99, noise_std=0.002, base_value=1.0)
    ticks = gen.generate_ticks(n=40)
    store = HistoricalStore.from_ticks(ticks[:-1])
    sample = ticks[-1]
    events = detect_measurement_anomalies(sample, store, z_threshold=4.0, spike_threshold=0.05)
    assert events == []


def test_zscore_vs_history() -> None:
    store = _hist([1.0] * 20)
    sample = [Measurement(TS + timedelta(minutes=20), "bus_1_vm_pu", 1.10, QualityFlag.GOOD)]
    events = detect_measurement_anomalies(sample, store, z_threshold=3.0, spike_threshold=0.5)
    assert len(events) >= 1
    assert events[0].type is AnomalyType.MEASUREMENT_ZSCORE
    assert isinstance(events[0], AnomalyEvent)
    assert events[0].signal_id == "bus_1_vm_pu"
    assert events[0].score > 0


def test_no_pf_residual_detector() -> None:
    """Ensure detect path never emits pf_residual in Stage 5."""
    store = _hist([1.0] * 10)
    sample = [Measurement(TS, "bus_1_vm_pu", 1.0, QualityFlag.GOOD)]
    events = detect_measurement_anomalies(sample, store)
    assert all(e.type != AnomalyType.PF_RESIDUAL for e in events)
