"""Plotly figures for Grid Pulse time-series UI."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go


def build_timeseries_figure(df: pd.DataFrame, signal_id: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["tick_index"],
            y=df["value"],
            mode="lines+markers",
            name=signal_id,
            line={"color": "#1f4e79"},
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
