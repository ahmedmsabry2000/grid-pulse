"""Continuous sparse/full synthetic tick simulator → append JSONL via run_tick."""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np

from gridpulse.config import DEFAULT_SETTINGS, Settings
from gridpulse.network import load_network
from gridpulse.pipeline import run_tick
from gridpulse.telemetry import HistoricalStore, Measurement, QualityFlag

DEFAULT_CHANNELS = ["bus_1_vm_pu", "bus_2_vm_pu", "bus_3_vm_pu"]


@dataclass
class LiveSimulator:
    """Seeded live generator: sparse meters by default, optional full coverage + inject."""

    channels: list[str] = field(default_factory=lambda: list(DEFAULT_CHANNELS))
    seed: int = 42
    full_coverage: bool = False
    inject_rate: float = 0.05
    history_warmup: int = 30
    network: str = "case14"
    noise_std: float = 0.002
    base_value: float = 1.0
    inject_spike_delta: float = 0.08
    settings: Settings = DEFAULT_SETTINGS
    start: datetime = field(
        default_factory=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    tick_delta: timedelta = field(default_factory=lambda: timedelta(seconds=1))

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        self._tick_clock = 0

    def _timestamp(self, tick_index: int) -> datetime:
        return self.start + tick_index * self.tick_delta

    def _select_channels(self) -> list[str]:
        if self.full_coverage or len(self.channels) <= 1:
            return list(self.channels)
        # At least one channel; omit at least one when possible for sparse mode.
        k = int(self._rng.integers(1, len(self.channels)))
        chosen = list(self._rng.choice(self.channels, size=k, replace=False))
        return sorted(chosen, key=self.channels.index)

    def generate_tick(self, tick_index: int) -> list[Measurement]:
        """Build one tick. Sparse: random subset. Full: all channels. Inject optional spike."""
        ts = self._timestamp(tick_index)
        selected = self._select_channels()
        inject = bool(self.inject_rate > 0 and self._rng.random() < self.inject_rate)
        inject_signal = (
            str(self._rng.choice(selected)) if inject and selected else None
        )
        row: list[Measurement] = []
        for signal_id in selected:
            if signal_id == inject_signal:
                value = self.base_value + self.inject_spike_delta
            else:
                noise = float(self._rng.normal(0.0, self.noise_std))
                value = self.base_value + noise
            row.append(
                Measurement(
                    timestamp=ts,
                    signal_id=signal_id,
                    value=value,
                    quality=QualityFlag.GOOD,
                )
            )
        return row

    def _warmup_history(self) -> HistoricalStore:
        """Quiet full-coverage history so detectors have a baseline."""
        ticks: list[list[Measurement]] = []
        quiet = LiveSimulator(
            channels=list(self.channels),
            seed=self.seed ^ 0xA5A5,
            full_coverage=True,
            inject_rate=0.0,
            history_warmup=0,
            network=self.network,
            noise_std=self.noise_std,
            base_value=self.base_value,
            settings=self.settings,
            start=self.start - self.history_warmup * self.tick_delta,
            tick_delta=self.tick_delta,
        )
        for i in range(self.history_warmup):
            ticks.append(quiet.generate_tick(i))
        return HistoricalStore.from_ticks(ticks)

    def run(
        self,
        path: str | Path,
        *,
        interval: float = 1.0,
        max_ticks: int | None = None,
        sleep_fn: Callable[[float], Any] | None = None,
    ) -> int:
        """Append pipeline JSONL ticks continuously (or until max_ticks).

        Opens the file in append mode — never truncates existing content.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        sleep = time.sleep if sleep_fn is None else sleep_fn
        store = self._warmup_history()
        net = load_network(self.network)
        previous: list[Measurement] | None = None
        written = 0
        with path.open("a", encoding="utf-8") as sink:
            while max_ticks is None or written < max_ticks:
                sample = self.generate_tick(written)
                rec = run_tick(
                    sample,
                    history=store,
                    network=self.network,
                    tick_index=written,
                    previous=previous,
                    settings=self.settings,
                    net=net,
                )
                sink.write(json.dumps(rec, sort_keys=True) + "\n")
                sink.flush()
                store.extend(sample)
                previous = sample
                written += 1
                if max_ticks is not None and written >= max_ticks:
                    break
                if interval > 0:
                    sleep(interval)
        return written
