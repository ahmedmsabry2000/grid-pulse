"""Measurement-fault detectors: spike/jump and z-score vs history."""

import math

from gridpulse.anomaly.types import AnomalyEvent, AnomalyType
from gridpulse.telemetry import HistoricalStore, Measurement


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


class SpikeDetector:
    """Absolute jump vs last history sample → unit-interval score."""

    name = "spike"

    def __init__(self, *, threshold: float = 0.05) -> None:
        self.threshold = threshold

    def score(self, measurement: Measurement, history: HistoricalStore) -> float:
        if measurement.value is None:
            return 0.0
        hist = [h.value for h in history.for_signal(measurement.signal_id) if h.value is not None]
        if not hist:
            return 0.0
        spike = abs(float(measurement.value) - float(hist[-1]))
        if self.threshold <= 0:
            return 1.0 if spike > 0 else 0.0
        return _clamp01(spike / self.threshold)


class ZScoreDetector:
    """Absolute z-score vs history → unit-interval score."""

    name = "zscore"

    def __init__(self, *, threshold: float = 3.0) -> None:
        self.threshold = threshold

    def score(self, measurement: Measurement, history: HistoricalStore) -> float:
        if measurement.value is None:
            return 0.0
        hist = [h.value for h in history.for_signal(measurement.signal_id) if h.value is not None]
        if not hist:
            return 0.0
        mean = sum(hist) / len(hist)
        var = sum((x - mean) ** 2 for x in hist) / len(hist)
        std = math.sqrt(var)
        deviation = abs(float(measurement.value) - mean)
        if std <= 1e-12:
            return 1.0 if deviation > 1e-9 else 0.0
        z = deviation / std
        if self.threshold <= 0:
            return 1.0 if z > 0 else 0.0
        return _clamp01(z / self.threshold)


def detect_measurement_anomalies(
    sample: list[Measurement],
    history: HistoricalStore,
    *,
    z_threshold: float = 3.0,
    spike_threshold: float = 0.05,
) -> list[AnomalyEvent]:
    """Detect measurement faults. Does not implement PF residual (F2)."""
    events: list[AnomalyEvent] = []
    for m in sample:
        if m.value is None:
            continue
        hist = [h.value for h in history.for_signal(m.signal_id) if h.value is not None]
        if not hist:
            continue

        last = hist[-1]
        spike = abs(float(m.value) - float(last))
        if spike >= spike_threshold:
            events.append(
                AnomalyEvent(
                    type=AnomalyType.MEASUREMENT_SPIKE,
                    signal_id=m.signal_id,
                    timestamp=m.timestamp,
                    value=m.value,
                    score=spike,
                    detail=f"spike {spike:.4f} >= {spike_threshold}",
                )
            )

        mean = sum(hist) / len(hist)
        var = sum((x - mean) ** 2 for x in hist) / len(hist)
        std = math.sqrt(var)
        deviation = abs(float(m.value) - mean)
        if std <= 1e-12:
            # Flat history: any material deviation is an infinite z
            if deviation > 1e-9:
                events.append(
                    AnomalyEvent(
                        type=AnomalyType.MEASUREMENT_ZSCORE,
                        signal_id=m.signal_id,
                        timestamp=m.timestamp,
                        value=m.value,
                        score=float("inf"),
                        detail="z=inf (zero-variance history)",
                    )
                )
        else:
            z = deviation / std
            if z >= z_threshold:
                events.append(
                    AnomalyEvent(
                        type=AnomalyType.MEASUREMENT_ZSCORE,
                        signal_id=m.signal_id,
                        timestamp=m.timestamp,
                        value=m.value,
                        score=z,
                        detail=f"z={z:.2f} >= {z_threshold}",
                    )
                )
    return events
