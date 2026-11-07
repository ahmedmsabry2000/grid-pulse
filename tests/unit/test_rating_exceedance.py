"""Rating exceedance detector — independent of historical anomaly scoring."""

from datetime import datetime, timezone

import pandapower as pp
import pytest

from gridpulse.anomaly import AnomalyType, detect_rating_exceedances
from gridpulse.anomaly.types import AnomalyEvent
from gridpulse.network import load_network
from gridpulse.pipeline import run_tick
from gridpulse.powerflow import run_powerflow
from gridpulse.quality import GateDecision, PowerflowGate
from gridpulse.telemetry import HistoricalStore, Measurement, QualityFlag, SyntheticTelemetryGenerator


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _converged_net_with_tight_line_limit() -> object:
    net = load_network("case14")
    sample = [
        Measurement(TS, "bus_1_vm_pu", 1.06, QualityFlag.GOOD),
        Measurement(TS, "bus_2_vm_pu", 1.045, QualityFlag.GOOD),
    ]
    gate = PowerflowGate().decide(sample, previous=None, net=net)
    assert gate.action is GateDecision.RUN
    result = run_powerflow(net, sample, gate=gate)
    assert result.converged and result.net is not None
    # Force every line over its loading limit without changing physics result.
    result.net.line["max_loading_percent"] = 0.01
    return result.net


def test_rating_exceedance_type_exists() -> None:
    assert AnomalyType.RATING_EXCEEDANCE.value == "rating_exceedance"
    assert AnomalyType.PF_RESIDUAL.value == "pf_residual"


def test_over_limit_fires_with_payload() -> None:
    net = _converged_net_with_tight_line_limit()
    events = detect_rating_exceedances(net, timestamp=TS)
    assert events
    assert all(e.type is AnomalyType.RATING_EXCEEDANCE for e in events)
    e = events[0]
    assert isinstance(e, AnomalyEvent)
    assert e.signal_id.startswith("line:") or e.signal_id.startswith("trafo:")
    assert e.quantity in {"loading_percent", "i_ka"}
    assert e.value is not None and e.limit is not None and e.margin is not None
    assert e.value > e.limit
    assert e.margin == pytest.approx(e.limit - e.value)


def test_under_limit_clean() -> None:
    net = load_network("case14")
    pp.runpp(net)
    events = detect_rating_exceedances(net, timestamp=TS)
    assert events == []


def test_skipped_pf_does_not_invent_ratings() -> None:
    signals = ["bus_1_vm_pu"]
    hist = SyntheticTelemetryGenerator(signals=signals, seed=0, noise_std=0.002).generate_ticks(n=20)
    sample = [
        Measurement(TS, "bus_1_vm_pu", None, QualityFlag.MISSING),
    ]
    rec = run_tick(sample, history_ticks=hist, network="case14", tick_index=0)
    assert rec["gate"]["action"] == "skip"
    assert rec["powerflow"]["ran"] is False
    assert all(a["type"] != "rating_exceedance" for a in rec["anomalies"])


def test_non_converged_pf_does_not_invent_ratings(monkeypatch: pytest.MonkeyPatch) -> None:
    signals = ["bus_1_vm_pu"]
    hist = SyntheticTelemetryGenerator(signals=signals, seed=0, noise_std=0.002).generate_ticks(n=20)
    sample = hist[-1]

    def _no_converge(net, sample, *, gate):
        from gridpulse.powerflow.runner import PowerflowResult

        return PowerflowResult(converged=False, net=None, error="forced")

    monkeypatch.setattr("gridpulse.pipeline.runner.run_powerflow", _no_converge)
    rec = run_tick(sample, history_ticks=hist[:-1], network="case14", tick_index=0)
    assert rec["powerflow"]["ran"] is True
    assert rec["powerflow"]["converged"] is False
    assert all(a["type"] != "rating_exceedance" for a in rec["anomalies"])


def test_pipeline_emits_rating_in_jsonl_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    signals = ["bus_1_vm_pu"]
    hist = SyntheticTelemetryGenerator(signals=signals, seed=0, noise_std=0.002).generate_ticks(n=20)
    sample = hist[-1]

    real_run = run_powerflow

    def _tight_limits(net, sample, *, gate):
        result = real_run(net, sample, gate=gate)
        if result.converged and result.net is not None:
            result.net.line["max_loading_percent"] = 0.01
        return result

    monkeypatch.setattr("gridpulse.pipeline.runner.run_powerflow", _tight_limits)
    rec = run_tick(sample, history_ticks=hist[:-1], network="case14", tick_index=0)
    ratings = [a for a in rec["anomalies"] if a["type"] == "rating_exceedance"]
    assert ratings
    a = ratings[0]
    assert "quantity" in a and "limit" in a and "margin" in a
    assert a["signal_id"]


def test_orthogonality_rating_independent_of_history() -> None:
    """Over-limit still emits rating even when history would call the reading normal."""
    net = _converged_net_with_tight_line_limit()
    rating_events = detect_rating_exceedances(net, timestamp=TS)
    assert rating_events

    # Flat history at the same measurement value → no historical spike/zscore.
    from gridpulse.anomaly import detect_measurement_anomalies

    store = HistoricalStore()
    for i in range(20):
        store.append(Measurement(TS, "bus_1_vm_pu", 1.06, QualityFlag.GOOD))
    sample = [Measurement(TS, "bus_1_vm_pu", 1.06, QualityFlag.GOOD)]
    hist_events = detect_measurement_anomalies(sample, store, z_threshold=3.0, spike_threshold=0.05)
    assert hist_events == []
    # Rating still stands — detectors are independent.
    assert all(e.type is AnomalyType.RATING_EXCEEDANCE for e in rating_events)
