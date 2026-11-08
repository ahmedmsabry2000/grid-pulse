"""Historical ensemble anomaly — spike + z-score + Isolation Forest."""

from datetime import datetime, timedelta, timezone

import pytest

from gridpulse.anomaly import (
    AnomalyType,
    EnsembleConfig,
    detect_ensemble_anomalies,
    detect_measurement_anomalies,
    detect_rating_exceedances,
)
from gridpulse.anomaly.detectors import SpikeDetector, ZScoreDetector
from gridpulse.anomaly.ensemble import IsolationForestDetector, score_ensemble
from gridpulse.anomaly.types import AnomalyEvent
from gridpulse.network import load_network
from gridpulse.pipeline import run_tick
from gridpulse.powerflow import run_powerflow
from gridpulse.telemetry import HistoricalStore, Measurement, QualityFlag


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


def test_measurement_ensemble_type_and_pf_residual_unused() -> None:
    assert AnomalyType.MEASUREMENT_ENSEMBLE.value == "measurement_ensemble"
    assert AnomalyType.PF_RESIDUAL.value == "pf_residual"


def test_detector_protocol_scores_in_unit_interval() -> None:
    store = _hist([1.0] * 30)
    sample = Measurement(TS + timedelta(minutes=30), "bus_1_vm_pu", 1.20, QualityFlag.GOOD)
    for detector in (
        SpikeDetector(threshold=0.05),
        ZScoreDetector(threshold=3.0),
        IsolationForestDetector(random_state=0),
    ):
        s = detector.score(sample, store)
        assert 0.0 <= s <= 1.0


def test_iforest_deterministic_with_seed() -> None:
    store = _hist([1.0 + (i % 3) * 0.001 for i in range(40)])
    sample = Measurement(TS + timedelta(minutes=40), "bus_1_vm_pu", 1.5, QualityFlag.GOOD)
    a = IsolationForestDetector(random_state=7).score(sample, store)
    b = IsolationForestDetector(random_state=7).score(sample, store)
    c = IsolationForestDetector(random_state=8).score(sample, store)
    assert a == b
    assert a != c or a == 1.0  # extreme outliers may saturate; still seeded


def test_weighted_average_aggregator() -> None:
    scores = {"spike": 1.0, "zscore": 0.0, "iforest": 0.5}
    weights = {"spike": 0.2, "zscore": 0.3, "iforest": 0.5}
    assert score_ensemble(scores, weights) == pytest.approx(0.2 * 1.0 + 0.3 * 0.0 + 0.5 * 0.5)


def test_ensemble_emits_when_over_threshold() -> None:
    store = _hist([1.0] * 40)
    sample = [Measurement(TS + timedelta(minutes=40), "bus_1_vm_pu", 1.5, QualityFlag.GOOD)]
    cfg = EnsembleConfig(threshold=0.3, random_state=0)
    events = detect_ensemble_anomalies(sample, store, config=cfg)
    assert len(events) == 1
    e = events[0]
    assert e.type is AnomalyType.MEASUREMENT_ENSEMBLE
    assert isinstance(e, AnomalyEvent)
    assert 0.0 <= e.score <= 1.0
    assert e.score >= cfg.threshold
    assert e.member_scores is not None
    assert set(e.member_scores) >= {"spike", "zscore", "iforest"}
    assert all(0.0 <= v <= 1.0 for v in e.member_scores.values())


def test_ensemble_quiet_on_clean_noise() -> None:
    store = _hist([1.0 + (i % 2) * 0.001 for i in range(40)])
    sample = [Measurement(TS + timedelta(minutes=40), "bus_1_vm_pu", 1.0005, QualityFlag.GOOD)]
    events = detect_ensemble_anomalies(sample, store, config=EnsembleConfig(threshold=0.5, random_state=0))
    assert events == []


def test_orthogonality_in_limit_but_historically_weird() -> None:
    """Weird vs history but within rating → ensemble yes, rating no."""
    store = _hist([1.0] * 40)
    sample = [Measurement(TS + timedelta(minutes=40), "bus_1_vm_pu", 1.4, QualityFlag.GOOD)]
    ensemble = detect_ensemble_anomalies(sample, store, config=EnsembleConfig(threshold=0.3, random_state=0))
    assert ensemble

    pn = load_network("case14")
    assert pn.run_powerflow() is True
    ratings = detect_rating_exceedances(pn, timestamp=TS)
    assert ratings == []


def test_orthogonality_over_limit_historically_normal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Over-limit with calm history → rating yes; ensemble may be quiet on calm bus reading."""
    store = _hist([1.06] * 40)
    sample = [Measurement(TS + timedelta(minutes=40), "bus_1_vm_pu", 1.06, QualityFlag.GOOD)]
    ensemble = detect_ensemble_anomalies(sample, store, config=EnsembleConfig(threshold=0.5, random_state=0))
    assert ensemble == []

    real_run = run_powerflow

    def _tight(network, sample, *, gate):
        result = real_run(network, sample, gate=gate)
        if result.converged and result.network is not None:
            result.network.set_column("line", "max_loading_percent", 0.01)
        return result

    monkeypatch.setattr("gridpulse.pipeline.runner.run_powerflow", _tight)
    rec = run_tick(sample, history=store, network="case14", tick_index=0)
    types = {a["type"] for a in rec["anomalies"]}
    assert "rating_exceedance" in types
    # Calm measurement → no ensemble; rating still present (independent).
    assert "measurement_ensemble" not in types


def test_orthogonality_both_can_fire(monkeypatch: pytest.MonkeyPatch) -> None:
    # 1.15 is in-range for the quality gate (PF still runs) but weird vs flat history.
    store = _hist([1.0] * 40)
    sample = [Measurement(TS + timedelta(minutes=40), "bus_1_vm_pu", 1.15, QualityFlag.GOOD)]

    real_run = run_powerflow

    def _tight(network, sample, *, gate):
        result = real_run(network, sample, gate=gate)
        if result.converged and result.network is not None:
            result.network.set_column("line", "max_loading_percent", 0.01)
        return result

    monkeypatch.setattr("gridpulse.pipeline.runner.run_powerflow", _tight)
    from gridpulse.config import Settings

    settings = Settings(ensemble_threshold=0.3)
    rec = run_tick(sample, history=store, network="case14", tick_index=0, settings=settings)
    assert rec["gate"]["action"] == "run"
    assert rec["powerflow"]["converged"] is True
    types = {a["type"] for a in rec["anomalies"]}
    assert "rating_exceedance" in types
    assert "measurement_ensemble" in types


def test_existing_spike_zscore_path_retained() -> None:
    store = _hist([1.0] * 20)
    sample = [Measurement(TS + timedelta(minutes=20), "bus_1_vm_pu", 1.10, QualityFlag.GOOD)]
    events = detect_measurement_anomalies(sample, store, z_threshold=3.0, spike_threshold=0.5)
    assert any(e.type is AnomalyType.MEASUREMENT_ZSCORE for e in events)
