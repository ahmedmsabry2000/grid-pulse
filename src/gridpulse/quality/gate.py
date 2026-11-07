"""Hard powerflow gate: any quality failure → Skip."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

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
        net: Any | None = None,
    ) -> Run | Skip:
        failures = validate_sample(sample, previous=previous, net=net)
        if not failures:
            return Run()
        first = failures[0]
        return Skip(reason=first.reason, detail=first.detail)
