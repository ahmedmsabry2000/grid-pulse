"""Streamlit time-series UI over live / Stage 6 JSONL events."""

from datetime import timedelta
from typing import Any

import streamlit as st

from gridpulse.config.paths import resolve_events_path
from gridpulse.ui.events import available_signals, load_events
from gridpulse.ui.plots import build_multiseries_figure
from gridpulse.ui.powerflow_panel import run_powerflow_on_latest
from gridpulse.ui.snapshots import append_snapshot, freeze_snapshot
from gridpulse.ui.tables import (
    flatten_anomaly_rows,
    flatten_ensemble_rows,
    flatten_rating_rows,
)

# Latest N ticks shown on the live chart
_TAIL_N = 200


def _render_pf_panels(result: dict[str, Any]) -> None:
    if not result.get("ok"):
        st.error(result.get("error") or "powerflow panel failed")
        return

    gate = result.get("gate") or {}
    pf = result.get("powerflow") or {}
    st.write(
        f"Gate: `{gate.get('action')}`"
        + (f" ({gate.get('reason')})" if gate.get("reason") else "")
    )
    if gate.get("action") == "skip":
        st.warning("Powerflow skipped by quality gate.")
    elif pf.get("ran") and pf.get("converged") is False:
        st.warning(f"Powerflow did not converge: {pf.get('error')}")
    elif pf.get("ran") and pf.get("converged"):
        st.success("Powerflow converged.")

    st.markdown("#### Rating exceedances")
    ratings = flatten_rating_rows(result.get("rating_exceedances") or [])
    if ratings:
        st.dataframe(ratings, use_container_width=True, hide_index=True)
    else:
        st.caption("None")

    st.markdown("#### Ensemble anomalies")
    ens = flatten_ensemble_rows(result.get("ensemble_anomalies") or [])
    if ens:
        st.dataframe(ens, use_container_width=True, hide_index=True)
    else:
        st.caption("None")

    other = flatten_anomaly_rows(result.get("other_anomalies") or [])
    if other:
        st.markdown("#### Other anomalies")
        st.dataframe(other, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="Grid Pulse", layout="wide")
    st.title("Grid Pulse")
    st.caption(
        "Auto-tails the fixed events stream. Simulator runs in a separate process — "
        "this UI never starts it. Each Run powerflow freezes an immutable snapshot."
    )

    if "snapshots" not in st.session_state:
        st.session_state.snapshots = []
    if "snapshot_index" not in st.session_state:
        st.session_state.snapshot_index = 0

    path = resolve_events_path()
    st.text(f"Events path: {path}")

    if not path.exists():
        st.warning(
            "JSONL file not found. In another terminal run: "
            "`uv run gridpulse-simulate` (or `uv run gridpulse --inject-faults` for a batch)."
        )
        return

    events = load_events(path)
    if not events:
        st.info("Events file is empty — waiting for the simulator to append ticks.")
        return

    tail = events[-_TAIL_N:]
    signals = available_signals(tail)
    if not signals:
        st.info("No measurements in file.")
        return

    @st.fragment(run_every=timedelta(seconds=2))
    def _live_chart() -> None:
        fresh = load_events(path)
        if not fresh:
            st.info("Waiting for ticks…")
            return
        window = fresh[-_TAIL_N:]
        chans = available_signals(window)
        if not chans:
            st.info("No measurements in window.")
            return
        fig = build_multiseries_figure(window, chans)
        st.plotly_chart(fig, use_container_width=True)
        st.write(
            f"Ticks shown: {len(window)} / {len(fresh)} total · "
            f"Channels: {len(chans)}"
        )

    _live_chart()

    st.subheader("Powerflow snapshots")
    if st.button("Run powerflow", type="primary"):
        fresh = load_events(path)
        result = run_powerflow_on_latest(fresh)
        snap = freeze_snapshot(fresh, result)
        st.session_state.snapshots, st.session_state.snapshot_index = append_snapshot(
            st.session_state.snapshots, snap
        )

    snapshots = st.session_state.snapshots
    if not snapshots:
        st.caption(
            "Press **Run powerflow** to freeze the stream up to now into a snapshot "
            "and show rating / ensemble panels. Live ticks only feed the next click."
        )
        return

    n = len(snapshots)
    idx = int(st.session_state.snapshot_index)
    idx = max(0, min(idx, n - 1))
    st.session_state.snapshot_index = idx

    nav_prev, nav_label, nav_next = st.columns([1, 3, 1])
    with nav_prev:
        if st.button("← Prev", disabled=idx <= 0):
            st.session_state.snapshot_index = idx - 1
            st.rerun()
    with nav_label:
        snap = snapshots[idx]
        st.markdown(
            f"**Snapshot {idx + 1} / {n}** · "
            f"ticks `{snap['tick_start']}`–`{snap['tick_end']}` "
            f"({snap['n_ticks']} frozen)"
        )
    with nav_next:
        if st.button("Next →", disabled=idx >= n - 1):
            st.session_state.snapshot_index = idx + 1
            st.rerun()

    _render_pf_panels(snapshots[st.session_state.snapshot_index]["result"])


if __name__ == "__main__":
    main()
