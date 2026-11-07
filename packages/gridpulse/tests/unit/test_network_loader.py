"""Stage 1: pluggable network loader."""

import copy

import pytest

from gridpulse.network import (
    UnknownNetworkError,
    list_networks,
    load_network,
    register_network,
)


def test_list_networks_includes_defaults() -> None:
    names = list_networks()
    assert "case9" in names
    assert "case14" in names
    assert "case30" in names
    assert names == sorted(names)


def test_load_case14_default() -> None:
    net = load_network()
    assert len(net.bus) == 14
    assert len(net.line) > 0


def test_load_case14_by_name() -> None:
    net = load_network("case14")
    assert len(net.bus) == 14


def test_isolation_via_copy() -> None:
    a = load_network("case14")
    b = load_network("case14")
    original_vm = float(a.bus.loc[0, "vn_kv"])
    a.bus.loc[0, "vn_kv"] = original_vm + 99.0
    assert float(b.bus.loc[0, "vn_kv"]) == original_vm


def test_unknown_id_raises() -> None:
    with pytest.raises(UnknownNetworkError, match="not-a-real-net"):
        load_network("not-a-real-net")


def test_registered_stub_network_loads() -> None:
    def _stub():
        # Minimal pandapower-like object with bus attribute for shape checks
        import pandapower as pp

        net = pp.create_empty_network()
        pp.create_bus(net, vn_kv=110.0)
        pp.create_bus(net, vn_kv=110.0)
        return net

    register_network("stub2", _stub)
    try:
        net = load_network("stub2")
        assert len(net.bus) == 2
        # Isolation still holds for registered nets
        other = load_network("stub2")
        net.bus.loc[0, "vn_kv"] = 999.0
        assert float(other.bus.loc[0, "vn_kv"]) == 110.0
    finally:
        from gridpulse.network.loader import _REGISTRY

        _REGISTRY.pop("stub2", None)
