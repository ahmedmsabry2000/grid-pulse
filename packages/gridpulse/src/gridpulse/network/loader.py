"""Pluggable network loader → PNetwork."""

from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandapower as pp
import pandapower.networks as pn

from gridpulse.network.pnetwork import PNetwork


class UnknownNetworkError(ValueError):
    """Raised when name_or_path is not a registered id or loadable path."""


NetworkFactory = Callable[[], Any]

_REGISTRY: dict[str, NetworkFactory] = {
    "case9": pn.case9,
    "case14": pn.case14,
    "case30": pn.case30,
}


def register_network(name: str, factory: NetworkFactory) -> None:
    """Register a network factory under ``name`` (overwrites if present)."""
    _REGISTRY[name] = factory


def list_networks() -> list[str]:
    """Return sorted registry ids (not file paths)."""
    return sorted(_REGISTRY)


def load_network(name_or_path: str = "case14") -> PNetwork:
    """Load an isolated ``PNetwork`` by registry id or file path.

    Returns a deep-copied pandapower net wrapped as ``PNetwork`` so callers
    cannot contaminate factory results or subsequent loads.
    """
    key = name_or_path
    if key in _REGISTRY:
        net = deepcopy(_REGISTRY[key]())
        return PNetwork.from_pandapower(key, net)

    path = Path(name_or_path)
    if path.is_file():
        net = deepcopy(pp.from_json(str(path)))
        return PNetwork.from_pandapower(str(path), net)

    raise UnknownNetworkError(f"Unknown network id or path: {name_or_path!r}")
