"""Synthetic graph layout → GeoJSON-ready bus/line FeatureCollections.

No real GIS: NetworkX spring or Kamada–Kawai with a fixed seed, cached per
(network_id, seed, algorithm). Layout uses the NetworkX graph from ``PNetwork``.
"""

from typing import Any, Literal

import networkx as nx

from gridpulse.network.loader import load_network
from gridpulse.network.pnetwork import PNetwork

Algorithm = Literal["spring", "kamada_kawai"]

_CACHE: dict[tuple[str, int, str], dict[str, Any]] = {}


def clear_layout_cache() -> None:
    """Drop all cached layouts (tests / hot-reload)."""
    _CACHE.clear()


def _positions(
    g: nx.Graph,
    *,
    seed: int,
    algorithm: Algorithm,
) -> dict[int, tuple[float, float]]:
    if algorithm == "kamada_kawai":
        # NetworkX KK has no seed; stabilize via spring init then KK polish.
        init = nx.spring_layout(g, seed=seed, dim=2)
        raw = nx.kamada_kawai_layout(g, pos=init, dim=2)
    else:
        raw = nx.spring_layout(g, seed=seed, dim=2)
    return {int(n): (float(xy[0]), float(xy[1])) for n, xy in raw.items()}


def _buses_geojson(pos: dict[int, tuple[float, float]]) -> dict[str, Any]:
    features = []
    for bus_id, (x, y) in sorted(pos.items()):
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [x, y]},
                "properties": {"bus_id": bus_id},
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _lines_geojson(pn: PNetwork, pos: dict[int, tuple[float, float]]) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    net = pn.pp_net
    for idx, row in net.line.iterrows():
        a, b = int(row.from_bus), int(row.to_bus)
        if a not in pos or b not in pos:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [list(pos[a]), list(pos[b])],
                },
                "properties": {
                    "line_id": int(idx),
                    "from_bus": a,
                    "to_bus": b,
                    "kind": "line",
                },
            }
        )
    if hasattr(net, "trafo") and len(net.trafo):
        for idx, row in net.trafo.iterrows():
            a, b = int(row.hv_bus), int(row.lv_bus)
            if a not in pos or b not in pos:
                continue
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [list(pos[a]), list(pos[b])],
                    },
                    "properties": {
                        "trafo_id": int(idx),
                        "from_bus": a,
                        "to_bus": b,
                        "kind": "trafo",
                    },
                }
            )
    return {"type": "FeatureCollection", "features": features}


def layout_network(
    network_id: str = "case14",
    *,
    seed: int = 42,
    algorithm: Algorithm = "spring",
) -> dict[str, Any]:
    """Return GeoJSON-ready topology for ``network_id``.

    Result shape::

        {
          "network_id": str,
          "seed": int,
          "algorithm": str,
          "buses": FeatureCollection(Point),
          "lines": FeatureCollection(LineString),
        }
    """
    key = (network_id, seed, algorithm)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    pn = load_network(network_id)
    pos = _positions(pn.graph, seed=seed, algorithm=algorithm)
    result = {
        "network_id": network_id,
        "seed": seed,
        "algorithm": algorithm,
        "buses": _buses_geojson(pos),
        "lines": _lines_geojson(pn, pos),
    }
    _CACHE[key] = result
    return result
