"""Detector protocol — members return a score in [0, 1]."""

from typing import Protocol

from gridpulse.telemetry import HistoricalStore, Measurement


class AnomalyDetector(Protocol):
    """Score one measurement against history in the unit interval."""

    name: str

    def score(self, measurement: Measurement, history: HistoricalStore) -> float:
        """Return anomaly score in ``[0, 1]`` (1 = most anomalous)."""
        ...
