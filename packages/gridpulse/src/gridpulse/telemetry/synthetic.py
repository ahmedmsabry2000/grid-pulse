"""Discrete offline synthetic telemetry generator."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import numpy as np

from gridpulse.telemetry.schemas import Measurement, QualityFlag


@dataclass(frozen=True, slots=True)
class FaultSpec:
    """Inject a fixed value (and optional quality) at a tick index."""

    tick_index: int
    signal_id: str
    value: float | None
    quality: QualityFlag = QualityFlag.GOOD


@dataclass
class SyntheticTelemetryGenerator:
    """Seeded N-tick generator with optional fault injection."""

    signals: list[str]
    seed: int = 0
    noise_std: float = 0.01
    base_value: float = 1.0
    start: datetime = field(
        default_factory=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    tick_delta: timedelta = field(default_factory=lambda: timedelta(minutes=1))
    faults: list[FaultSpec] = field(default_factory=list)

    def generate_ticks(self, n: int) -> list[list[Measurement]]:
        rng = np.random.default_rng(self.seed)
        fault_map = {(f.tick_index, f.signal_id): f for f in self.faults}
        ticks: list[list[Measurement]] = []
        for i in range(n):
            ts = self.start + i * self.tick_delta
            row: list[Measurement] = []
            for signal_id in self.signals:
                key = (i, signal_id)
                if key in fault_map:
                    f = fault_map[key]
                    row.append(
                        Measurement(
                            timestamp=ts,
                            signal_id=signal_id,
                            value=f.value,
                            quality=f.quality,
                        )
                    )
                else:
                    noise = float(rng.normal(0.0, self.noise_std))
                    row.append(
                        Measurement(
                            timestamp=ts,
                            signal_id=signal_id,
                            value=self.base_value + noise,
                            quality=QualityFlag.GOOD,
                        )
                    )
            ticks.append(row)
        return ticks
