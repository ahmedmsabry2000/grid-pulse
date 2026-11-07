"""Stage 4: powerflow runner with convergence handling."""

from datetime import datetime, timezone

import pytest

from gridpulse.network import load_network
from gridpulse.powerflow import PowerflowError, PowerflowResult, run_powerflow
from gridpulse.quality import GateDecision, PowerflowGate
from gridpulse.telemetry import Measurement, QualityFlag


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _sample_for_case14() -> list[Measurement]:
    # Mild load adjustments that should still converge
    return [
        Measurement(TS, "load_0_p_mw", 20.0, QualityFlag.GOOD),
        Measurement(TS, "bus_1_vm_pu", 1.06, QualityFlag.GOOD),
    ]


def test_nominal_converges() -> None:
    net = load_network("case14")
    sample = _sample_for_case14()
    gate = PowerflowGate().decide(sample, net=net)
    assert gate.action is GateDecision.RUN
    result = run_powerflow(net, sample, gate=gate)
    assert isinstance(result, PowerflowResult)
    assert result.converged is True


def test_requires_gate_run() -> None:
    net = load_network("case14")
    sample = [
        Measurement(TS, "bus_1_vm_pu", None, QualityFlag.MISSING),
    ]
    gate = PowerflowGate().decide(sample, net=net)
    assert gate.action is GateDecision.SKIP
    with pytest.raises(PowerflowError, match="gate"):
        run_powerflow(net, sample, gate=gate)


def test_stressed_fails_cleanly() -> None:
    net = load_network("case14")
    # Extreme loads to force non-convergence (within quality ranges)
    sample = [
        Measurement(TS, f"load_{i}_p_mw", 400.0, QualityFlag.GOOD)
        for i in range(min(5, len(net.load)))
    ]
    # Bypass gate intentionally with a synthetic Run to stress PF itself
    from gridpulse.quality import Run

    result = run_powerflow(net, sample, gate=Run())
    assert result.converged is False
    assert result.error is not None
