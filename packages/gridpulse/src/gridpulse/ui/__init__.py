"""Streamlit + Plotly time-series UI helpers.

Plotly figure builders live in ``gridpulse.ui.plots`` and are imported
explicitly so non-UI consumers (e.g. web-server) can use events/panel helpers
without the ``ui`` optional extra.
"""

from gridpulse.ui.events import available_signals, load_events, series_frame
from gridpulse.ui.snapshots import append_snapshot, freeze_snapshot

__all__ = [
    "append_snapshot",
    "available_signals",
    "freeze_snapshot",
    "load_events",
    "series_frame",
]
