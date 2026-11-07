"""Stage 6: pipeline batch with injected faults → JSONL + events."""

import json
from io import StringIO
from pathlib import Path

from gridpulse.pipeline import run_batch, run_tick
from gridpulse.telemetry import FaultSpec, QualityFlag, SyntheticTelemetryGenerator


def test_run_batch_emits_skips_and_anomalies(tmp_path: Path) -> None:
    signals = ["bus_1_vm_pu", "bus_2_vm_pu"]
    faults = [
        FaultSpec(tick_index=5, signal_id="bus_1_vm_pu", value=None, quality=QualityFlag.MISSING),
        FaultSpec(tick_index=8, signal_id="bus_2_vm_pu", value=1.15),
    ]
    gen = SyntheticTelemetryGenerator(
        signals=signals, seed=42, noise_std=0.002, base_value=1.0, faults=faults
    )
    # Warm-up history ticks without faults for anomaly baseline
    history_ticks = SyntheticTelemetryGenerator(
        signals=signals, seed=1, noise_std=0.002, base_value=1.0
    ).generate_ticks(n=25)

    out_path = tmp_path / "events.jsonl"
    stdout = StringIO()
    records = run_batch(
        ticks=gen.generate_ticks(n=10),
        history_ticks=history_ticks,
        network="case14",
        jsonl_path=out_path,
        stdout=stdout,
    )

    assert len(records) == 10
    assert out_path.exists()
    lines = out_path.read_text().strip().splitlines()
    assert len(lines) == 10
    parsed = [json.loads(line) for line in lines]
    assert any(r["gate"]["action"] == "skip" for r in parsed)
    assert any(r.get("anomalies") for r in parsed)
    # stdout mirrors JSONL lines
    assert stdout.getvalue().strip().splitlines() == lines


def test_run_tick_structure() -> None:
    signals = ["bus_1_vm_pu"]
    hist = SyntheticTelemetryGenerator(signals=signals, seed=0, noise_std=0.002).generate_ticks(n=20)
    sample = SyntheticTelemetryGenerator(signals=signals, seed=0, noise_std=0.002).generate_ticks(n=21)[-1]
    rec = run_tick(sample, history_ticks=hist, network="case14", tick_index=20)
    assert rec["tick_index"] == 20
    assert "gate" in rec
    assert "powerflow" in rec
    assert "anomalies" in rec
    assert "measurements" in rec
