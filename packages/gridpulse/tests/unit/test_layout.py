"""Synthetic NetworkX layout → GeoJSON-ready buses/lines."""

import gridpulse.network.layout as layout_mod
from gridpulse.network.layout import clear_layout_cache, layout_network


def setup_function() -> None:
    clear_layout_cache()


def test_layout_case14_has_buses_and_lines() -> None:
    topo = layout_network("case14", seed=42)
    assert topo["network_id"] == "case14"
    buses = topo["buses"]
    lines = topo["lines"]
    assert buses["type"] == "FeatureCollection"
    assert lines["type"] == "FeatureCollection"
    assert len(buses["features"]) == 14
    assert len(lines["features"]) > 0
    for feat in buses["features"]:
        assert feat["geometry"]["type"] == "Point"
        coords = feat["geometry"]["coordinates"]
        assert len(coords) == 2
        assert all(isinstance(c, (int, float)) for c in coords)
        assert "bus_id" in feat["properties"]
    for feat in lines["features"]:
        assert feat["geometry"]["type"] == "LineString"
        assert len(feat["geometry"]["coordinates"]) == 2


def test_layout_deterministic_same_seed() -> None:
    a = layout_network("case14", seed=7)
    b = layout_network("case14", seed=7)
    assert a["buses"] == b["buses"]
    assert a["lines"] == b["lines"]


def test_layout_cache_per_network_and_seed() -> None:
    first = layout_network("case14", seed=1)
    second = layout_network("case14", seed=1)
    assert first is second  # cached object identity
    other = layout_network("case14", seed=2)
    assert other is not first
    assert other["buses"] != first["buses"]


def test_layout_kamada_kawai_algorithm() -> None:
    topo = layout_network("case14", seed=42, algorithm="kamada_kawai")
    assert len(topo["buses"]["features"]) == 14
    spring = layout_network("case14", seed=42, algorithm="spring")
    # Different algorithms with same seed generally differ
    assert topo["buses"] != spring["buses"]
