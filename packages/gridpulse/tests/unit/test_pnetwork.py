"""PNetwork: pandapower + NetworkX domain type."""

from datetime import datetime, timezone

import networkx as nx
import pytest

from gridpulse.network import PNetwork, UnknownNetworkError, load_network
from gridpulse.telemetry import Measurement, QualityFlag


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_load_network_returns_pnetwork() -> None:
    pn = load_network("case14")
    assert isinstance(pn, PNetwork)
    assert pn.name == "case14"
    assert pn.bus_count == 14
    assert pn.line_count > 0
    assert isinstance(pn.graph, nx.Graph)
    assert pn.graph.number_of_nodes() == 14


def test_graph_matches_topology() -> None:
    pn = load_network("case14")
    assert pn.graph.number_of_nodes() == pn.bus_count
    # Every line endpoints are graph edges
    for u, v in pn.line_endpoints():
        assert pn.graph.has_edge(u, v) or pn.graph.has_edge(v, u)


def test_isolation_via_copy() -> None:
    a = load_network("case14")
    b = load_network("case14")
    original = a.bus_vn_kv(0)
    a.set_bus_vn_kv(0, original + 99.0)
    assert b.bus_vn_kv(0) == original
    assert a.bus_vn_kv(0) == original + 99.0


def test_copy_is_independent() -> None:
    a = load_network("case14")
    b = a.copy()
    a.set_bus_vn_kv(0, a.bus_vn_kv(0) + 1.0)
    assert b.bus_vn_kv(0) != a.bus_vn_kv(0)


def test_apply_measurements_mutates_only_via_method() -> None:
    pn = load_network("case14")
    before = float(pn.pp_net.load.at[0, "p_mw"])
    pn.apply_measurements(
        [Measurement(TS, "load_0_p_mw", before + 5.0, QualityFlag.GOOD)]
    )
    assert float(pn.pp_net.load.at[0, "p_mw"]) == pytest.approx(before + 5.0)


def test_run_powerflow_on_pnetwork() -> None:
    pn = load_network("case14")
    assert pn.run_powerflow() is True
    assert pn.converged is True


def test_unknown_still_raises() -> None:
    with pytest.raises(UnknownNetworkError):
        load_network("not-a-real-net")
