"""Stage 1: pluggable network loader → PNetwork."""

import pytest

from gridpulse.network import (
    PNetwork,
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
    pn = load_network()
    assert isinstance(pn, PNetwork)
    assert pn.bus_count == 14
    assert pn.line_count > 0


def test_load_case14_by_name() -> None:
    pn = load_network("case14")
    assert pn.bus_count == 14


def test_isolation_via_copy() -> None:
    a = load_network("case14")
    b = load_network("case14")
    original_vm = a.bus_vn_kv(0)
    a.set_bus_vn_kv(0, original_vm + 99.0)
    assert b.bus_vn_kv(0) == original_vm


def test_unknown_id_raises() -> None:
    with pytest.raises(UnknownNetworkError, match="not-a-real-net"):
        load_network("not-a-real-net")


def test_registered_stub_network_loads() -> None:
    def _stub():
        import pandapower as pp

        net = pp.create_empty_network()
        pp.create_bus(net, vn_kv=110.0)
        pp.create_bus(net, vn_kv=110.0)
        return net

    register_network("stub2", _stub)
    try:
        pn = load_network("stub2")
        assert pn.bus_count == 2
        other = load_network("stub2")
        pn.set_bus_vn_kv(0, 999.0)
        assert other.bus_vn_kv(0) == 110.0
    finally:
        from gridpulse.network.loader import _REGISTRY

        _REGISTRY.pop("stub2", None)
