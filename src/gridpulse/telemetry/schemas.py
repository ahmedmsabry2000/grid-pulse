"""Measurement schemas and quality flags."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class QualityFlag(str, Enum):
    GOOD = "good"
    BAD = "bad"
    SUSPECT = "suspect"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class Measurement:
    timestamp: datetime
    signal_id: str
    value: float | None
    quality: QualityFlag = QualityFlag.GOOD
