"""Live simulator: sparse/full coverage, inject, append, CLI."""

import json
from pathlib import Path

from gridpulse.simulator import LiveSimulator, DEFAULT_CHANNELS
from gridpulse.simulator.cli import main as simulate_main
from gridpulse.telemetry import Measurement


def test_sparse_tick_omits_channels() -> None:
    sim = LiveSimulator(
        channels=["bus_1_vm_pu", "bus_2_vm_pu", "bus_3_vm_pu"],
        seed=7,
        full_coverage=False,
        inject_rate=0.0,
    )
    # Warm RNG into a sparse draw; collect several ticks
    sizes = []
    for i in range(20):
        tick = sim.generate_tick(i)
        ids = {m.signal_id for m in tick}
        assert ids.issubset(set(sim.channels))
        assert len(tick) >= 1
        assert len(tick) < len(sim.channels) or True  # may occasionally be full by chance
        sizes.append(len(tick))
        # Omitted channels are absent — not fabricated as MISSING
        for m in tick:
            assert isinstance(m, Measurement)
            assert m.value is not None
    assert min(sizes) < len(sim.channels), "sparse mode should omit some channels across ticks"


def test_full_coverage_includes_all_channels() -> None:
    sim = LiveSimulator(
        channels=["bus_1_vm_pu", "bus_2_vm_pu", "bus_3_vm_pu"],
        seed=0,
        full_coverage=True,
        inject_rate=0.0,
    )
    for i in range(5):
        tick = sim.generate_tick(i)
        assert {m.signal_id for m in tick} == set(sim.channels)
        assert len(tick) == len(sim.channels)


def test_inject_produces_anomaly_events_through_pipeline(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    sim = LiveSimulator(
        channels=["bus_1_vm_pu", "bus_2_vm_pu", "bus_3_vm_pu"],
        seed=42,
        full_coverage=True,
        inject_rate=1.0,  # always inject
        history_warmup=30,
        network="case14",
    )
    n = sim.run(path, interval=0.0, max_ticks=5, sleep_fn=lambda _s: None)
    assert n == 5
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 5
    records = [json.loads(line) for line in lines]
    assert any(r.get("anomalies") for r in records), "inject_rate=1 should yield anomaly-typed events"


def test_append_does_not_truncate(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text('{"tick_index": -1, "gate": {}, "powerflow": {}, "anomalies": [], "measurements": []}\n')
    before = path.read_text(encoding="utf-8")
    sim = LiveSimulator(
        channels=list(DEFAULT_CHANNELS),
        seed=1,
        full_coverage=True,
        inject_rate=0.0,
        history_warmup=5,
    )
    sim.run(path, interval=0.0, max_ticks=2, sleep_fn=lambda _s: None)
    after = path.read_text(encoding="utf-8")
    assert after.startswith(before)
    assert len(after.strip().splitlines()) == 3  # 1 preexisting + 2 new


def test_cli_max_ticks_and_flags(tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "sim.jsonl"
    monkeypatch.setenv("GRIDPULSE_EVENTS_PATH", str(out))
    code = simulate_main(
        [
            "--interval",
            "0",
            "--max-ticks",
            "3",
            "--full-coverage",
            "--inject-rate",
            "0.5",
            "--seed",
            "99",
        ]
    )
    assert code == 0
    assert out.exists()
    assert len(out.read_text(encoding="utf-8").strip().splitlines()) == 3
