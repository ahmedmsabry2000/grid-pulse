"""Streamlit time-series UI over Stage 6 JSONL events."""

from pathlib import Path

import streamlit as st

from gridpulse.ui.events import available_signals, load_events, series_frame
from gridpulse.ui.plots import build_timeseries_figure


def main() -> None:
    st.set_page_config(page_title="Grid Pulse", layout="wide")
    st.title("Grid Pulse")
    st.caption("Measurement series from Stage 6 JSONL — anomalies and gate skips marked.")

    default = Path("events.jsonl")
    path_str = st.text_input("JSONL path", value=str(default if default.exists() else "events.jsonl"))
    path = Path(path_str)
    if not path.exists():
        st.warning("JSONL file not found. Run: `uv run gridpulse --inject-faults --jsonl events.jsonl`")
        return

    events = load_events(path)
    signals = available_signals(events)
    if not signals:
        st.info("No measurements in file.")
        return

    signal = st.selectbox("Signal", signals, index=0)
    df = series_frame(events, signal)
    fig = build_timeseries_figure(df, signal)
    st.plotly_chart(fig, use_container_width=True)

    skips = int(df["is_skip"].sum())
    anoms = int(df["is_anomaly"].sum())
    st.write(f"Ticks: {len(df)} · Gate skips: {skips} · Anomaly ticks: {anoms}")
    st.dataframe(df, use_container_width=True)


if __name__ == "__main__":
    main()
