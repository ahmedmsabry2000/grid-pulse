"""Anomaly event types — measurement faults, rating exceedance; pf_residual reserved."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AnomalyType(str, Enum):
    MEASUREMENT_SPIKE = "measurement_spike"
    MEASUREMENT_ZSCORE = "measurement_zscore"
    RATING_EXCEEDANCE = "rating_exceedance"
    MEASUREMENT_ENSEMBLE = "measurement_ensemble"
    # Reserved for future physics residual detectors (F2) — not implemented in MVP:
    PF_RESIDUAL = "pf_residual"


@dataclass(frozen=True, slots=True)
class AnomalyEvent:
    type: AnomalyType
    signal_id: str
    timestamp: datetime
    value: float | None
    score: float
    detail: str = ""
    # Rating exceedance payload (optional; independent of historical scoring)
    quantity: str | None = None
    limit: float | None = None
    margin: float | None = None
    # Ensemble payload (optional; independent of rating exceedance)
    member_scores: dict[str, float] | None = None
