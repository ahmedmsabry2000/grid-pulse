"""Stage 3: validators and hard powerflow gate."""

from copy import deepcopy
from datetime import datetime, timezone

import pytest

from gridpulse.network import load_network
from gridpulse.quality import (
    GateDecision,
    PowerflowGate,
    ReasonCode,
    Skip,
    validate_sample,
)
from gridpulse.telemetry import Measurement, QualityFlag


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _m(signal_id: str, value: float | None, quality: QualityFlag = QualityFlag.GOOD) -> Measurement:
    return Measurement(timestamp=TS, signal_id=signal_id, value=value, quality=quality)


def test_good_sample_runs() -> None:
    sample = [
        _m("bus_1_vm_pu", 1.01),
        _m("bus_2_vm_pu", 0.99),
        _m("load_3_p_mw", 10.0),
    ]
    prev = [
        _m("bus_1_vm_pu", 1.00),
        _m("bus_2_vm_pu", 0.98),
        _m("load_3_p_mw", 9.5),
    ]
    gate = PowerflowGate()
    decision = gate.decide(sample, previous=prev)
    assert decision.action is GateDecision.RUN
    assert isinstance(decision, type(decision))  # Run path
    assert decision.reason is None


def test_missing_value_skips() -> None:
    sample = [_m("bus_1_vm_pu", None, QualityFlag.MISSING)]
    decision = PowerflowGate().decide(sample)
    assert decision.action is GateDecision.SKIP
    assert decision.reason is ReasonCode.MISSING


def test_bad_quality_flag_skips() -> None:
    sample = [_m("bus_1_vm_pu", 1.0, QualityFlag.BAD)]
    decision = PowerflowGate().decide(sample)
    assert decision.action is GateDecision.SKIP
    assert decision.reason is ReasonCode.BAD_QUALITY


def test_out_of_range_skips() -> None:
    sample = [_m("bus_1_vm_pu", 2.5)]  # default vm range ~0.8-1.2
    decision = PowerflowGate().decide(sample)
    assert decision.action is GateDecision.SKIP
    assert decision.reason is ReasonCode.OUT_OF_RANGE


def test_rate_of_change_skips() -> None:
    prev = [_m("bus_1_vm_pu", 1.0)]
    # Still in range [0.8, 1.2] but delta 0.18 > default roc 0.15
    sample = [_m("bus_1_vm_pu", 1.18)]
    decision = PowerflowGate().decide(sample, previous=prev)
    assert decision.action is GateDecision.SKIP
    assert decision.reason is ReasonCode.RATE_OF_CHANGE


def test_topology_inconsistency_skips() -> None:
    # Signal references bus that does not exist on case14 (buses 1..14 typically)
    sample = [_m("bus_999_vm_pu", 1.0)]
    net = load_network("case14")
    decision = PowerflowGate().decide(sample, net=net)
    assert decision.action is GateDecision.SKIP
    assert decision.reason is ReasonCode.TOPOLOGY


def test_gate_does_not_mutate_net() -> None:
    net = load_network("case14")
    before = deepcopy(net)
    sample = [_m("bus_1_vm_pu", 1.0)]
    PowerflowGate().decide(sample, net=net)
    assert net.bus.equals(before.bus)
    assert net.load.equals(before.load)


def test_validate_sample_reports_failures() -> None:
    sample = [_m("bus_1_vm_pu", None, QualityFlag.MISSING)]
    failures = validate_sample(sample)
    assert ReasonCode.MISSING in [f.reason for f in failures]


def test_any_failure_hard_skips() -> None:
    # Mix: one good, one bad → Skip (hard policy D4)
    sample = [_m("bus_1_vm_pu", 1.0), _m("bus_2_vm_pu", 9.0)]
    decision = PowerflowGate().decide(sample)
    assert decision.action is GateDecision.SKIP
    assert isinstance(decision, Skip)
