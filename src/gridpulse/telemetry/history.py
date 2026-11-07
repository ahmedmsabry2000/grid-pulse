"""In-memory historical measurement store."""

from gridpulse.telemetry.schemas import Measurement


class HistoricalStore:
    """Append-only history keyed by signal_id."""

    def __init__(self) -> None:
        self._by_signal: dict[str, list[Measurement]] = {}

    def append(self, measurement: Measurement) -> None:
        self._by_signal.setdefault(measurement.signal_id, []).append(measurement)

    def extend(self, measurements: list[Measurement]) -> None:
        for m in measurements:
            self.append(m)

    def for_signal(self, signal_id: str) -> list[Measurement]:
        return list(self._by_signal.get(signal_id, []))

    def all(self) -> list[Measurement]:
        out: list[Measurement] = []
        for items in self._by_signal.values():
            out.extend(items)
        return out

    @classmethod
    def from_ticks(cls, ticks: list[list[Measurement]]) -> "HistoricalStore":
        store = cls()
        for tick in ticks:
            store.extend(tick)
        return store
