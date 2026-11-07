"""Pluggable pandapower network loader."""

from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandapower as pp
import pandapower.networks as pn


class UnknownNetworkError(ValueError):
    """Raised when name_or_path is not a registered id or loadable path."""


NetworkFactory = Callable[[], Any]

_REGISTRY: dict[str, NetworkFactory] = {
    "case14": pn.case14,
}


def register_network(name: str, factory: NetworkFactory) -> None:
    """Register a network factory under ``name`` (overwrites if present)."""
    _REGISTRY[name] = factory


def load_network(name_or_path: str = "case14") -> Any:
    """Load an isolated pandapower network by registry id or file path.

    Returns a deep copy so callers cannot mutate the shared factory result
    or contaminate subsequent loads.
    """
    key = name_or_path
    if key in _REGISTRY:
        net = _REGISTRY[key]()
        return deepcopy(net)

    path = Path(name_or_path)
    if path.is_file():
        net = pp.from_json(str(path))
        return deepcopy(net)

    raise UnknownNetworkError(f"Unknown network id or path: {name_or_path!r}")
