"""Anomaly event types — measurement faults now; pf_residual reserved (D2a)."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AnomalyType(str, Enum):
    MEASUREMENT_SPIKE = "measurement_spike"
    MEASUREMENT_ZSCORE = "measurement_zscore"
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
