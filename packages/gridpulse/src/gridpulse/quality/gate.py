"""Hard powerflow gate: any quality failure → Skip."""

from dataclasses import dataclass
from enum import Enum

from gridpulse.network import PNetwork
from gridpulse.quality.reasons import ReasonCode
from gridpulse.quality.validators import validate_sample
from gridpulse.telemetry import Measurement


class GateDecision(str, Enum):
    RUN = "run"
    SKIP = "skip"


@dataclass(frozen=True, slots=True)
class Run:
    action: GateDecision = GateDecision.RUN
    reason: ReasonCode | None = None


@dataclass(frozen=True, slots=True)
class Skip:
    reason: ReasonCode
    action: GateDecision = GateDecision.SKIP
    detail: str = ""


class PowerflowGate:
    """Sole PF authorizer. Hard-skip on any quality failure (D4)."""

    def decide(
        self,
        sample: list[Measurement],
        *,
        previous: list[Measurement] | None = None,
        network: PNetwork | None = None,
    ) -> Run | Skip:
        failures = validate_sample(sample, previous=previous, network=network)
        if not failures:
            return Run()
        first = failures[0]
        return Skip(reason=first.reason, detail=first.detail)
