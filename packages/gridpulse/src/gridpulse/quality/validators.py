"""Sample validators: missing, range, rate-of-change, topology."""

from dataclasses import dataclass
from typing import Any

from gridpulse.quality.reasons import ReasonCode
from gridpulse.telemetry import Measurement, QualityFlag

# Default ranges by signal suffix / prefix heuristics
_DEFAULT_RANGES: dict[str, tuple[float, float]] = {
    "vm_pu": (0.8, 1.2),
    "p_mw": (-500.0, 500.0),
    "q_mvar": (-500.0, 500.0),
}

_DEFAULT_ROC: dict[str, float] = {
    "vm_pu": 0.15,
    "p_mw": 50.0,
    "q_mvar": 50.0,
}


@dataclass(frozen=True, slots=True)
class ValidationFailure:
    reason: ReasonCode
    signal_id: str
    detail: str = ""


def _kind(signal_id: str) -> str | None:
    for key in _DEFAULT_RANGES:
        if signal_id.endswith(key) or f"_{key}" in signal_id:
            return key
    return None


def _bus_index(signal_id: str) -> int | None:
    # Expect patterns like bus_1_vm_pu
    parts = signal_id.split("_")
    if len(parts) >= 2 and parts[0] == "bus":
        try:
            return int(parts[1])
        except ValueError:
            return None
    return None


def validate_sample(
    sample: list[Measurement],
    *,
    previous: list[Measurement] | None = None,
    net: Any | None = None,
) -> list[ValidationFailure]:
    """Return all validation failures (empty means OK)."""
    failures: list[ValidationFailure] = []
    prev_by_id = {m.signal_id: m for m in (previous or [])}

    for m in sample:
        if m.value is None or m.quality is QualityFlag.MISSING:
            failures.append(
                ValidationFailure(ReasonCode.MISSING, m.signal_id, "missing value")
            )
            continue
        if m.quality is QualityFlag.BAD:
            failures.append(
                ValidationFailure(ReasonCode.BAD_QUALITY, m.signal_id, "bad quality flag")
            )
            continue

        kind = _kind(m.signal_id)
        if kind and kind in _DEFAULT_RANGES:
            lo, hi = _DEFAULT_RANGES[kind]
            if not (lo <= float(m.value) <= hi):
                failures.append(
                    ValidationFailure(
                        ReasonCode.OUT_OF_RANGE,
                        m.signal_id,
                        f"value {m.value} outside [{lo}, {hi}]",
                    )
                )
                continue

        if previous is not None and m.signal_id in prev_by_id and kind:
            prev = prev_by_id[m.signal_id]
            if prev.value is not None and kind in _DEFAULT_ROC:
                delta = abs(float(m.value) - float(prev.value))
                if delta > _DEFAULT_ROC[kind]:
                    failures.append(
                        ValidationFailure(
                            ReasonCode.RATE_OF_CHANGE,
                            m.signal_id,
                            f"delta {delta} exceeds {_DEFAULT_ROC[kind]}",
                        )
                    )
                    continue

        if net is not None:
            bus_idx = _bus_index(m.signal_id)
            if bus_idx is not None:
                # pandapower case14 uses 0-based bus index; signals use 1-based labels
                max_bus = len(net.bus)
                if bus_idx < 1 or bus_idx > max_bus:
                    failures.append(
                        ValidationFailure(
                            ReasonCode.TOPOLOGY,
                            m.signal_id,
                            f"bus {bus_idx} not in network (1..{max_bus})",
                        )
                    )

    return failures
