"""Stage 8: CLI smoke + golden fixture contract."""

from pathlib import Path

from gridpulse.pipeline.cli import main
from gridpulse.ui.events import available_signals, load_events, series_frame


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_golden_events_fixture() -> None:
    path = FIXTURES / "golden_events.jsonl"
    events = load_events(path)
    assert len(events) == 3
    assert available_signals(events) == ["bus_1_vm_pu", "bus_2_vm_pu"]
    df = series_frame(events, "bus_1_vm_pu")
    assert bool(df.loc[1, "is_skip"])
    assert bool(df.loc[2, "is_anomaly"])


def test_cli_writes_jsonl(tmp_path: Path, capsys) -> None:
    out = tmp_path / "out.jsonl"
    code = main(["--ticks", "3", "--history", "5", "--jsonl", str(out), "--inject-faults"])
    assert code == 0
    assert out.exists()
    lines = out.read_text().strip().splitlines()
    assert len(lines) == 3
    captured = capsys.readouterr()
    assert captured.out.strip().splitlines() == lines


def test_historical_store_all() -> None:
    from gridpulse.telemetry import HistoricalStore, Measurement, QualityFlag
    from datetime import datetime, timezone

    store = HistoricalStore()
    store.append(
        Measurement(datetime(2026, 1, 1, tzinfo=timezone.utc), "a", 1.0, QualityFlag.GOOD)
    )
    store.append(
        Measurement(datetime(2026, 1, 1, tzinfo=timezone.utc), "b", 2.0, QualityFlag.GOOD)
    )
    assert len(store.all()) == 2
