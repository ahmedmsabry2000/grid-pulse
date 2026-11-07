"""Powerflow runner — only after gate Run."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import pandapower as pp

from gridpulse.quality import GateDecision, Run, Skip
from gridpulse.telemetry import Measurement


class PowerflowError(RuntimeError):
    """Raised when PF is invoked without a Run decision."""


@dataclass(frozen=True, slots=True)
class PowerflowResult:
    converged: bool
    net: Any | None = None
    error: str | None = None


def _apply_sample(net: Any, sample: list[Measurement]) -> None:
    for m in sample:
        if m.value is None:
            continue
        parts = m.signal_id.split("_")
        if parts[0] == "load" and len(parts) >= 3:
            try:
                idx = int(parts[1])
            except ValueError:
                continue
            if idx not in net.load.index:
                continue
            field = "_".join(parts[2:])
            if field in net.load.columns:
                net.load.at[idx, field] = float(m.value)
        elif parts[0] == "bus" and len(parts) >= 3 and parts[-2:] == ["vm", "pu"]:
            try:
                bus_label = int(parts[1])
            except ValueError:
                continue
            bus_idx = bus_label - 1  # 1-based signal → 0-based index
            gens = net.gen.index[net.gen.bus == bus_idx]
            for g in gens:
                net.gen.at[g, "vm_pu"] = float(m.value)


def run_powerflow(
    net: Any,
    sample: list[Measurement],
    *,
    gate: Run | Skip,
) -> PowerflowResult:
    """Apply sample on a net copy and run AC powerflow.

    Requires ``gate.action == RUN``. Non-convergence returns
    ``PowerflowResult(converged=False, error=...)`` — not success.
    """
    if gate.action is not GateDecision.RUN:
        raise PowerflowError("powerflow refused: gate did not return Run")

    working = deepcopy(net)
    _apply_sample(working, sample)
    try:
        pp.runpp(working)
        converged = bool(working.converged)
        if not converged:
            return PowerflowResult(converged=False, net=working, error="not converged")
        return PowerflowResult(converged=True, net=working)
    except Exception as exc:  # pandapower raises on hard failures
        return PowerflowResult(converged=False, error=str(exc))
