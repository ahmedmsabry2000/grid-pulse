"""Powerflow runner — only after gate Run; operates on PNetwork."""

from dataclasses import dataclass

from gridpulse.network import PNetwork
from gridpulse.quality import GateDecision, Run, Skip
from gridpulse.telemetry import Measurement


class PowerflowError(RuntimeError):
    """Raised when PF is invoked without a Run decision."""


@dataclass(frozen=True, slots=True)
class PowerflowResult:
    converged: bool
    network: PNetwork | None = None
    error: str | None = None


def run_powerflow(
    network: PNetwork,
    sample: list[Measurement],
    *,
    gate: Run | Skip,
) -> PowerflowResult:
    """Apply sample on a PNetwork copy and run AC powerflow.

    Requires ``gate.action == RUN``. Non-convergence returns
    ``PowerflowResult(converged=False, error=...)`` — not success.
    """
    if gate.action is not GateDecision.RUN:
        raise PowerflowError("powerflow refused: gate did not return Run")

    working = network.copy()
    working.apply_measurements(sample)
    try:
        converged = working.run_powerflow()
        if not converged:
            return PowerflowResult(converged=False, network=working, error="not converged")
        return PowerflowResult(converged=True, network=working)
    except Exception as exc:  # pandapower raises on hard failures
        return PowerflowResult(converged=False, error=str(exc))
