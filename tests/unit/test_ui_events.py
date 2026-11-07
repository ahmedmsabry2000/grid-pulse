"""Stage 7: UI event loading and figure construction from JSONL."""

import json
from pathlib import Path

from gridpulse.ui.events import load_events, series_frame
from gridpulse.ui.plots import build_timeseries_figure


def _write_sample(path: Path) -> None:
    records = [
        {
            "tick_index": 0,
            "gate": {"action": "run", "reason": None},
            "powerflow": {"ran": True, "converged": True, "error": None},
            "anomalies": [],
            "measurements": [
                {
                    "timestamp": "2026-01-01T00:00:00+00:00",
                    "signal_id": "bus_1_vm_pu",
                    "value": 1.0,
                    "quality": "good",
                }
            ],
        },
        {
            "tick_index": 1,
            "gate": {"action": "skip", "reason": "missing"},
            "powerflow": {"ran": False, "converged": None, "error": None},
            "anomalies": [],
            "measurements": [
                {
                    "timestamp": "2026-01-01T00:01:00+00:00",
                    "signal_id": "bus_1_vm_pu",
                    "value": None,
                    "quality": "missing",
                }
            ],
        },
        {
            "tick_index": 2,
            "gate": {"action": "run", "reason": None},
            "powerflow": {"ran": True, "converged": True, "error": None},
            "anomalies": [
                {
                    "type": "measurement_spike",
                    "signal_id": "bus_1_vm_pu",
                    "timestamp": "2026-01-01T00:02:00+00:00",
                    "value": 1.12,
                    "score": 0.12,
                    "detail": "spike",
                }
            ],
            "measurements": [
                {
                    "timestamp": "2026-01-01T00:02:00+00:00",
                    "signal_id": "bus_1_vm_pu",
                    "value": 1.12,
                    "quality": "good",
                }
            ],
        },
    ]
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def test_load_events(tmp_path: Path) -> None:
    p = tmp_path / "events.jsonl"
    _write_sample(p)
    events = load_events(p)
    assert len(events) == 3
    assert events[1]["gate"]["action"] == "skip"


def test_series_frame_and_figure(tmp_path: Path) -> None:
    p = tmp_path / "events.jsonl"
    _write_sample(p)
    events = load_events(p)
    df = series_frame(events, signal_id="bus_1_vm_pu")
    assert list(df["tick_index"]) == [0, 1, 2]
    assert df.loc[2, "is_anomaly"] is True or bool(df.loc[2, "is_anomaly"])
    assert df.loc[1, "is_skip"] is True or bool(df.loc[1, "is_skip"])
    fig = build_timeseries_figure(df, signal_id="bus_1_vm_pu")
    assert fig is not None
    assert len(fig.data) >= 1


def test_series_frame_marks_rating_exceedance_tick_level(tmp_path: Path) -> None:
    """Rating events use object ids; still mark the tick for any selected signal."""
    records = [
        {
            "tick_index": 0,
            "gate": {"action": "run", "reason": None},
            "powerflow": {"ran": True, "converged": True, "error": None},
            "anomalies": [
                {
                    "type": "rating_exceedance",
                    "signal_id": "line:0",
                    "timestamp": "2026-01-01T00:00:00+00:00",
                    "value": 120.0,
                    "score": 20.0,
                    "detail": "loading_percent over",
                    "quantity": "loading_percent",
                    "limit": 100.0,
                    "margin": -20.0,
                }
            ],
            "measurements": [
                {
                    "timestamp": "2026-01-01T00:00:00+00:00",
                    "signal_id": "bus_1_vm_pu",
                    "value": 1.0,
                    "quality": "good",
                }
            ],
        }
    ]
    p = tmp_path / "events.jsonl"
    p.write_text(json.dumps(records[0]) + "\n", encoding="utf-8")
    df = series_frame(load_events(p), signal_id="bus_1_vm_pu")
    assert bool(df.loc[0, "is_anomaly"])
    assert "rating_exceedance" in df.loc[0, "anomaly_types"]
