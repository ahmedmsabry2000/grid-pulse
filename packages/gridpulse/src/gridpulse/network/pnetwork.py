"""PNetwork — foundational domain type (pandapower net + NetworkX graph)."""

from copy import deepcopy
from collections.abc import Iterable
from typing import Any

import networkx as nx
import pandapower as pp

from gridpulse.telemetry import Measurement


def graph_from_pandapower(net: Any) -> nx.Graph:
    """Build an undirected topology graph from a pandapower net."""
    g = nx.Graph()
    for bus_id in net.bus.index:
        g.add_node(int(bus_id))
    for _, row in net.line.iterrows():
        g.add_edge(int(row.from_bus), int(row.to_bus))
    if hasattr(net, "trafo") and len(net.trafo):
        for _, row in net.trafo.iterrows():
            g.add_edge(int(row.hv_bus), int(row.lv_bus))
    return g


class PNetwork:
    """Wraps a pandapower net and its corresponding NetworkX graph.

    Public mutation of pandapower state must go through methods on this type.
    ``pp_net`` is available for read access (results tables, validators).
    """

    __slots__ = ("name", "_net", "_graph")

    def __init__(self, name: str, net: Any, graph: nx.Graph | None = None) -> None:
        self.name = name
        self._net = net
        self._graph = graph if graph is not None else graph_from_pandapower(net)

    @classmethod
    def from_pandapower(cls, name: str, net: Any) -> "PNetwork":
        """Wrap an isolated (caller-owned) pandapower net."""
        return cls(name, net)

    @property
    def graph(self) -> nx.Graph:
        return self._graph

    @property
    def pp_net(self) -> Any:
        """Underlying pandapower net (read-oriented; mutate via methods)."""
        return self._net

    @property
    def bus_count(self) -> int:
        return len(self._net.bus)

    @property
    def line_count(self) -> int:
        return len(self._net.line)

    @property
    def load_count(self) -> int:
        return len(self._net.load)

    @property
    def converged(self) -> bool:
        return bool(getattr(self._net, "converged", False))

    def copy(self) -> "PNetwork":
        return PNetwork(self.name, deepcopy(self._net), self._graph.copy())

    def sync_graph(self) -> None:
        """Rebuild the NetworkX graph from the current pandapower topology."""
        self._graph = graph_from_pandapower(self._net)

    def bus_vn_kv(self, bus_idx: int) -> float:
        return float(self._net.bus.loc[bus_idx, "vn_kv"])

    def set_bus_vn_kv(self, bus_idx: int, value: float) -> None:
        self._net.bus.loc[bus_idx, "vn_kv"] = float(value)

    def set_column(self, table: str, column: str, value: Any) -> None:
        """Set an entire element-table column (e.g. tighten rating limits)."""
        df = getattr(self._net, table)
        df[column] = value

    def line_endpoints(self) -> Iterable[tuple[int, int]]:
        for _, row in self._net.line.iterrows():
            yield int(row.from_bus), int(row.to_bus)
        if hasattr(self._net, "trafo") and len(self._net.trafo):
            for _, row in self._net.trafo.iterrows():
                yield int(row.hv_bus), int(row.lv_bus)

    def apply_measurements(self, sample: list[Measurement]) -> None:
        """Apply measurement values onto loads / generator setpoints."""
        for m in sample:
            if m.value is None:
                continue
            parts = m.signal_id.split("_")
            if parts[0] == "load" and len(parts) >= 3:
                try:
                    idx = int(parts[1])
                except ValueError:
                    continue
                if idx not in self._net.load.index:
                    continue
                field = "_".join(parts[2:])
                if field in self._net.load.columns:
                    self._net.load.at[idx, field] = float(m.value)
            elif parts[0] == "bus" and len(parts) >= 3 and parts[-2:] == ["vm", "pu"]:
                try:
                    bus_label = int(parts[1])
                except ValueError:
                    continue
                bus_idx = bus_label - 1  # 1-based signal → 0-based index
                gens = self._net.gen.index[self._net.gen.bus == bus_idx]
                for g in gens:
                    self._net.gen.at[g, "vm_pu"] = float(m.value)

    def run_powerflow(self) -> bool:
        """Run AC powerflow in place; return whether it converged.

        Propagates pandapower hard failures to the caller.
        """
        pp.runpp(self._net)
        return bool(self._net.converged)
