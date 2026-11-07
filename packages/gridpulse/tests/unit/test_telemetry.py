"""Stage 2: telemetry schemas and synthetic batch ticks."""

from datetime import datetime, timezone

import pytest

from gridpulse.telemetry import (
    FaultSpec,
    HistoricalStore,
    Measurement,
    QualityFlag,
    SyntheticTelemetryGenerator,
)


def test_measurement_schema() -> None:
    m = Measurement(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        signal_id="bus_1_vm_pu",
        value=1.02,
        quality=QualityFlag.GOOD,
    )
    assert m.signal_id == "bus_1_vm_pu"
    assert m.quality is QualityFlag.GOOD
    assert m.value == 1.02


def test_seed_reproducibility() -> None:
    signals = ["bus_1_vm_pu", "bus_2_vm_pu"]
    g1 = SyntheticTelemetryGenerator(signals=signals, seed=42, noise_std=0.01)
    g2 = SyntheticTelemetryGenerator(signals=signals, seed=42, noise_std=0.01)
    t1 = g1.generate_ticks(n=5)
    t2 = g2.generate_ticks(n=5)
    assert t1 == t2
    assert len(t1) == 5
    assert all(len(tick) == 2 for tick in t1)


def test_seed_divergence() -> None:
    signals = ["bus_1_vm_pu"]
    a = SyntheticTelemetryGenerator(signals=signals, seed=1).generate_ticks(n=3)
    b = SyntheticTelemetryGenerator(signals=signals, seed=2).generate_ticks(n=3)
    assert a != b


def test_fault_injection_present() -> None:
    signals = ["bus_1_vm_pu", "load_3_p_mw"]
    faults = [
        FaultSpec(tick_index=2, signal_id="bus_1_vm_pu", value=9.99),
        FaultSpec(tick_index=4, signal_id="load_3_p_mw", value=-1.0, quality=QualityFlag.BAD),
    ]
    gen = SyntheticTelemetryGenerator(signals=signals, seed=7, faults=faults)
    ticks = gen.generate_ticks(n=5)
    weird = next(m for m in ticks[2] if m.signal_id == "bus_1_vm_pu")
    assert weird.value == pytest.approx(9.99)
    bad = next(m for m in ticks[4] if m.signal_id == "load_3_p_mw")
    assert bad.value == pytest.approx(-1.0)
    assert bad.quality is QualityFlag.BAD


def test_historical_store_roundtrip() -> None:
    store = HistoricalStore()
    m = Measurement(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        signal_id="bus_1_vm_pu",
        value=1.0,
        quality=QualityFlag.GOOD,
    )
    store.append(m)
    store.extend(
        [
            Measurement(
                timestamp=datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc),
                signal_id="bus_1_vm_pu",
                value=1.01,
                quality=QualityFlag.GOOD,
            )
        ]
    )
    hist = store.for_signal("bus_1_vm_pu")
    assert len(hist) == 2
    assert hist[0].value == 1.0
    assert store.for_signal("missing") == []


def test_historical_from_ticks() -> None:
    gen = SyntheticTelemetryGenerator(signals=["a"], seed=0)
    ticks = gen.generate_ticks(n=3)
    store = HistoricalStore.from_ticks(ticks)
    assert len(store.for_signal("a")) == 3
