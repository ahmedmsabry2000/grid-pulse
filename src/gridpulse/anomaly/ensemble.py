"""Weighted ensemble of unit-interval detectors (spike, z-score, Isolation Forest)."""

import math
from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import IsolationForest

from gridpulse.anomaly.detectors import SpikeDetector, ZScoreDetector
from gridpulse.anomaly.types import AnomalyEvent, AnomalyType
from gridpulse.telemetry import HistoricalStore, Measurement

# Documented defaults: spike / z-score / Isolation Forest.
DEFAULT_WEIGHTS: dict[str, float] = {
    "spike": 0.3,
    "zscore": 0.3,
    "iforest": 0.4,
}


@dataclass(frozen=True, slots=True)
class EnsembleConfig:
    """Weighted-average ensemble thresholds and member weights."""

    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    threshold: float = 0.5
    spike_threshold: float = 0.05
    z_threshold: float = 3.0
    random_state: int = 0
    min_history: int = 10


def score_ensemble(scores: dict[str, float], weights: dict[str, float]) -> float:
    """Weighted average of member scores; missing weights treated as 0."""
    total_w = 0.0
    acc = 0.0
    for name, score in scores.items():
        w = float(weights.get(name, 0.0))
        if w <= 0.0:
            continue
        acc += w * float(score)
        total_w += w
    if total_w <= 0.0:
        return 0.0
    return acc / total_w


class IsolationForestDetector:
    """Fit Isolation Forest on a history batch; score one point in [0, 1].

    No online / streaming fit — each call refits on the provided history window.
    """

    name = "iforest"

    def __init__(self, *, random_state: int = 0, min_history: int = 10) -> None:
        self.random_state = random_state
        self.min_history = min_history

    def score(self, measurement: Measurement, history: HistoricalStore) -> float:
        if measurement.value is None:
            return 0.0
        hist = [h.value for h in history.for_signal(measurement.signal_id) if h.value is not None]
        if len(hist) < self.min_history:
            return 0.0
        x_train = np.asarray(hist, dtype=float).reshape(-1, 1)
        model = IsolationForest(
            n_estimators=50,
            contamination="auto",
            random_state=self.random_state,
        )
        model.fit(x_train)
        # decision_function: higher = more normal. Map to anomaly in (0, 1).
        decision = float(model.decision_function([[float(measurement.value)]])[0])
        return float(1.0 / (1.0 + math.exp(decision)))


def detect_ensemble_anomalies(
    sample: list[Measurement],
    history: HistoricalStore,
    *,
    config: EnsembleConfig | None = None,
) -> list[AnomalyEvent]:
    """Emit ``measurement_ensemble`` when weighted score ≥ threshold.

    Independent of rating exceedance — never suppressed by limit checks.
    Keeps ``pf_residual`` unused.
    """
    cfg = config or EnsembleConfig()
    detectors = [
        SpikeDetector(threshold=cfg.spike_threshold),
        ZScoreDetector(threshold=cfg.z_threshold),
        IsolationForestDetector(random_state=cfg.random_state, min_history=cfg.min_history),
    ]
    events: list[AnomalyEvent] = []
    for m in sample:
        if m.value is None:
            continue
        hist = [h.value for h in history.for_signal(m.signal_id) if h.value is not None]
        if not hist:
            continue
        member_scores = {d.name: float(d.score(m, history)) for d in detectors}
        ensemble = score_ensemble(member_scores, cfg.weights)
        if ensemble < cfg.threshold:
            continue
        breakdown = ", ".join(f"{k}={v:.3f}" for k, v in sorted(member_scores.items()))
        events.append(
            AnomalyEvent(
                type=AnomalyType.MEASUREMENT_ENSEMBLE,
                signal_id=m.signal_id,
                timestamp=m.timestamp,
                value=m.value,
                score=ensemble,
                detail=f"ensemble={ensemble:.3f} >= {cfg.threshold} [{breakdown}]",
                member_scores=member_scores,
            )
        )
    return events
