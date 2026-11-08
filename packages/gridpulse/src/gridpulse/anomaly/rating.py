"""Rating exceedance detector — compare PF results to object limits."""

from datetime import datetime
from typing import Any

from gridpulse.anomaly.types import AnomalyEvent, AnomalyType
from gridpulse.network import PNetwork


def _maybe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def _check_element(
    *,
    kind: str,
    idx: Any,
    quantity: str,
    value: float | None,
    limit: float | None,
    timestamp: datetime,
) -> AnomalyEvent | None:
    if value is None or limit is None:
        return None
    if value <= limit:
        return None
    margin = limit - value
    return AnomalyEvent(
        type=AnomalyType.RATING_EXCEEDANCE,
        signal_id=f"{kind}:{idx}",
        timestamp=timestamp,
        value=value,
        score=abs(margin),
        detail=f"{quantity}={value:.6g} > limit={limit:.6g} (margin={margin:.6g})",
        quantity=quantity,
        limit=limit,
        margin=margin,
    )


def detect_rating_exceedances(network: PNetwork, *, timestamp: datetime) -> list[AnomalyEvent]:
    """Flag lines/trafos whose PF results exceed ratings.

    Requires a converged ``PNetwork`` with ``res_*`` tables. Compares
    ``loading_percent`` to ``max_loading_percent`` and, for lines,
    ``i_ka`` to ``max_i_ka`` when those columns exist.
    """
    events: list[AnomalyEvent] = []
    net = network.pp_net

    if hasattr(net, "line") and hasattr(net, "res_line") and len(net.res_line):
        for idx in net.res_line.index:
            if idx not in net.line.index:
                continue
            row = net.line.loc[idx]
            res = net.res_line.loc[idx]
            max_loading = _maybe_float(row["max_loading_percent"]) if "max_loading_percent" in net.line.columns else None
            loading = _maybe_float(res["loading_percent"]) if "loading_percent" in net.res_line.columns else None
            ev = _check_element(
                kind="line",
                idx=idx,
                quantity="loading_percent",
                value=loading,
                limit=max_loading,
                timestamp=timestamp,
            )
            if ev is not None:
                events.append(ev)

            max_i = _maybe_float(row["max_i_ka"]) if "max_i_ka" in net.line.columns else None
            i_ka = _maybe_float(res["i_ka"]) if "i_ka" in net.res_line.columns else None
            ev = _check_element(
                kind="line",
                idx=idx,
                quantity="i_ka",
                value=i_ka,
                limit=max_i,
                timestamp=timestamp,
            )
            if ev is not None:
                events.append(ev)

    if hasattr(net, "trafo") and hasattr(net, "res_trafo") and len(net.res_trafo):
        for idx in net.res_trafo.index:
            if idx not in net.trafo.index:
                continue
            row = net.trafo.loc[idx]
            res = net.res_trafo.loc[idx]
            max_loading = (
                _maybe_float(row["max_loading_percent"]) if "max_loading_percent" in net.trafo.columns else None
            )
            loading = _maybe_float(res["loading_percent"]) if "loading_percent" in net.res_trafo.columns else None
            ev = _check_element(
                kind="trafo",
                idx=idx,
                quantity="loading_percent",
                value=loading,
                limit=max_loading,
                timestamp=timestamp,
            )
            if ev is not None:
                events.append(ev)

    return events
