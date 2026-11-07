"""Plotly figures for Grid Pulse time-series UI."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go

from gridpulse.ui.events import series_frame

# Distinct qualitative palette for multi-channel traces (no purple-on-white bias).
_CHANNEL_COLORS = [
    "#1f4e79",
    "#c44e52",
    "#2a9d8f",
    "#e8a838",
    "#264653",
    "#e76f51",
    "#457b9d",
    "#8ab17d",
    "#bc6c25",
    "#6d597a",
    "#355070",
    "#b56576",
]


def build_timeseries_figure(df: pd.DataFrame, signal_id: str) -> go.Figure:
    """Single-channel figure (kept for tests / helpers). Prefer multiseries in the UI."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["tick_index"],
            y=df["value"],
            mode="lines+markers",
            name=signal_id,
            line={"color": _CHANNEL_COLORS[0]},
        )
    )

    skips = df[df["is_skip"]]
    if not skips.empty:
        fig.add_trace(
            go.Scatter(
                x=skips["tick_index"],
                y=skips["value"],
                mode="markers",
                name="gate skip",
                marker={"symbol": "x", "size": 12, "color": "#c44e52"},
            )
        )

    anoms = df[df["is_anomaly"]]
    if not anoms.empty:
        fig.add_trace(
            go.Scatter(
                x=anoms["tick_index"],
                y=anoms["value"],
                mode="markers",
                name="anomaly",
                marker={"symbol": "diamond", "size": 11, "color": "#e8a838"},
            )
        )

    fig.update_layout(
        title=f"{signal_id} over ticks",
        xaxis_title="tick",
        yaxis_title="value",
        template="plotly_white",
        legend={"orientation": "h"},
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
    )
    return fig


def build_multiseries_figure(
    events: list[dict[str, Any]],
    signal_ids: list[str],
) -> go.Figure:
    """One Plotly graph: every channel as a differently colored trace + legend."""
    fig = go.Figure()
    anomaly_x: list[Any] = []
    anomaly_y: list[Any] = []
    skip_x: list[Any] = []
    skip_y: list[Any] = []

    for i, signal_id in enumerate(signal_ids):
        df = series_frame(events, signal_id)
        color = _CHANNEL_COLORS[i % len(_CHANNEL_COLORS)]
        fig.add_trace(
            go.Scatter(
                x=df["tick_index"],
                y=df["value"],
                mode="lines+markers",
                name=signal_id,
                line={"color": color},
                marker={"color": color, "size": 6},
            )
        )
        skips = df[df["is_skip"] & df["value"].notna()]
        if not skips.empty:
            skip_x.extend(skips["tick_index"].tolist())
            skip_y.extend(skips["value"].tolist())
        anoms = df[df["is_anomaly"] & df["value"].notna()]
        if not anoms.empty:
            anomaly_x.extend(anoms["tick_index"].tolist())
            anomaly_y.extend(anoms["value"].tolist())

    if skip_x:
        fig.add_trace(
            go.Scatter(
                x=skip_x,
                y=skip_y,
                mode="markers",
                name="gate skip",
                marker={"symbol": "x", "size": 12, "color": "#c44e52"},
                legendgroup="markers",
            )
        )
    if anomaly_x:
        fig.add_trace(
            go.Scatter(
                x=anomaly_x,
                y=anomaly_y,
                mode="markers",
                name="anomaly",
                marker={"symbol": "diamond", "size": 11, "color": "#e8a838"},
                legendgroup="markers",
            )
        )

    fig.update_layout(
        title="All channels over ticks",
        xaxis_title="tick",
        yaxis_title="value",
        template="plotly_white",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
        margin={"l": 40, "r": 20, "t": 60, "b": 40},
    )
    return fig
