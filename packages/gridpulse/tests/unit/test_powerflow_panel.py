"""UI powerflow panel: latest-tick re-run, orthogonal rating vs ensemble lists."""

from datetime import datetime, timezone

from gridpulse.telemetry import QualityFlag, SyntheticTelemetryGenerator
from gridpulse.ui.powerflow_panel import (
    measurements_from_event,
    run_powerflow_on_latest,
)


def test_measurements_from_event_roundtrip() -> None:
    ev = {
        "measurements": [
            {
                "timestamp": "2026-01-01T00:00:00+00:00",
                "signal_id": "bus_1_vm_pu",
                "value": 1.01,
                "quality": "good",
            }
        ]
    }
    ms = measurements_from_event(ev)
    assert len(ms) == 1
    assert ms[0].signal_id == "bus_1_vm_pu"
    assert ms[0].value == 1.01
    assert ms[0].quality is QualityFlag.GOOD
    assert ms[0].timestamp == datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_run_powerflow_on_latest_empty() -> None:
    result = run_powerflow_on_latest([])
    assert result["ok"] is False
    assert result["rating_exceedances"] == []
    assert result["ensemble_anomalies"] == []


def test_run_powerflow_on_latest_separates_anomaly_kinds() -> None:
    signals = ["bus_1_vm_pu", "bus_2_vm_pu"]
    hist = SyntheticTelemetryGenerator(
        signals=signals, seed=1, noise_std=0.002, base_value=1.0
    ).generate_ticks(n=25)
    # Build synthetic event stream: quiet history then a spike on the last tick
    events = []
    for i, tick in enumerate(hist):
        events.append(
            {
                "tick_index": i,
                "gate": {"action": "run", "reason": None},
                "powerflow": {"ran": True, "converged": True, "error": None},
                "anomalies": [],
                "measurements": [
                    {
                        "timestamp": m.timestamp.isoformat(),
                        "signal_id": m.signal_id,
                        "value": m.value,
                        "quality": m.quality.value,
                    }
                    for m in tick
                ],
            }
        )
    spike_ts = hist[-1][0].timestamp
    events.append(
        {
            "tick_index": len(hist),
            "gate": {"action": "run", "reason": None},
            "powerflow": {"ran": True, "converged": True, "error": None},
            "anomalies": [],
            "measurements": [
                {
                    "timestamp": spike_ts.isoformat(),
                    "signal_id": "bus_1_vm_pu",
                    "value": 1.12,
                    "quality": "good",
                },
                {
                    "timestamp": spike_ts.isoformat(),
                    "signal_id": "bus_2_vm_pu",
                    "value": 1.0,
                    "quality": "good",
                },
            ],
        }
    )
    result = run_powerflow_on_latest(events, network="case14")
    assert result["ok"] is True
    assert result["gate"]["action"] in {"run", "skip"}
    # Orthogonal list keys always present
    assert isinstance(result["rating_exceedances"], list)
    assert isinstance(result["ensemble_anomalies"], list)
    # Spike should surface as measurement and/or ensemble anomaly
    types = {a["type"] for a in (result["record"] or {}).get("anomalies", [])}
    assert types & {"measurement_spike", "measurement_zscore", "measurement_ensemble"}
