"""Flatten Stage 6 anomaly payloads into operator table rows (no nested dicts)."""

from typing import Any


def _fmt_members(member_scores: Any) -> str:
    if not isinstance(member_scores, dict) or not member_scores:
        return "—"
    parts = []
    for key in sorted(member_scores):
        val = member_scores[key]
        if isinstance(val, (int, float)):
            parts.append(f"{key}={float(val):.3f}")
        else:
            parts.append(f"{key}={val}")
    return ", ".join(parts) if parts else "—"


def flatten_ensemble_rows(anomalies: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Flat ensemble rows: signal, score, detail, members (string)."""
    out: list[dict[str, Any]] = []
    for a in anomalies or []:
        out.append(
            {
                "signal": a.get("signal_id"),
                "score": a.get("score"),
                "detail": a.get("detail"),
                "members": _fmt_members(a.get("member_scores")),
            }
        )
    return out


def flatten_anomaly_rows(anomalies: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Scalar columns only — safe for st.dataframe without nested cells."""
    out: list[dict[str, Any]] = []
    for a in anomalies or []:
        out.append(
            {
                "type": a.get("type"),
                "signal": a.get("signal_id"),
                "score": a.get("score"),
                "detail": a.get("detail"),
                "value": a.get("value"),
                "quantity": a.get("quantity"),
                "limit": a.get("limit"),
                "margin": a.get("margin"),
            }
        )
    return out


def flatten_rating_rows(ratings: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Rating exceedance table, worst margin first."""
    rows: list[dict[str, Any]] = []
    for a in ratings or []:
        rows.append(
            {
                "object": a.get("signal_id"),
                "quantity": a.get("quantity"),
                "value": a.get("value"),
                "limit": a.get("limit"),
                "margin": a.get("margin"),
            }
        )
    rows.sort(
        key=lambda r: (
            r["margin"] if isinstance(r.get("margin"), (int, float)) else float("inf")
        )
    )
    return rows
