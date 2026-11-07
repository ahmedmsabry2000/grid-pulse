"""Streamlit time-series UI over live / Stage 6 JSONL events."""

from datetime import timedelta

import streamlit as st

from gridpulse.config.paths import resolve_events_path
from gridpulse.ui.events import available_signals, load_events, series_frame
from gridpulse.ui.plots import build_timeseries_figure
from gridpulse.ui.powerflow_panel import run_powerflow_on_latest

# Latest N ticks shown on the live chart
_TAIL_N = 200


def main() -> None:
    st.set_page_config(page_title="Grid Pulse", layout="wide")
    st.title("Grid Pulse")
    st.caption(
        "Auto-tails the fixed events stream. Simulator runs in a separate process — "
        "this UI never starts it."
    )

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

    col_chart, col_pf = st.columns([2, 1])

    with col_chart:
        signal = st.selectbox("Signal", signals, index=0)

        @st.fragment(run_every=timedelta(seconds=2))
        def _live_chart() -> None:
            fresh = load_events(path)
            if not fresh:
                st.info("Waiting for ticks…")
                return
            window = fresh[-_TAIL_N:]
            df = series_frame(window, signal)
            fig = build_timeseries_figure(df, signal)
            st.plotly_chart(fig, use_container_width=True)
            skips = int(df["is_skip"].sum()) if len(df) else 0
            anoms = int(df["is_anomaly"].sum()) if len(df) else 0
            st.write(
                f"Ticks shown: {len(df)} / {len(fresh)} total · "
                f"Gate skips: {skips} · Anomaly ticks: {anoms}"
            )

        _live_chart()

    with col_pf:
        st.subheader("Powerflow")
        if st.button("Run powerflow", type="primary"):
            fresh = load_events(path)
            st.session_state["pf_result"] = run_powerflow_on_latest(fresh)

        result = st.session_state.get("pf_result")
        if result is None:
            st.caption("Press **Run powerflow** to evaluate the latest tick.")
        elif not result.get("ok"):
            st.error(result.get("error") or "powerflow panel failed")
        else:
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
            ratings = result.get("rating_exceedances") or []
            if ratings:
                st.dataframe(
                    [
                        {
                            "object": a.get("signal_id"),
                            "quantity": a.get("quantity"),
                            "value": a.get("value"),
                            "limit": a.get("limit"),
                            "margin": a.get("margin"),
                        }
                        for a in ratings
                    ],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.caption("None")

            st.markdown("#### Ensemble anomalies")
            ens = result.get("ensemble_anomalies") or []
            if ens:
                st.dataframe(
                    [
                        {
                            "signal": a.get("signal_id"),
                            "score": a.get("score"),
                            "detail": a.get("detail"),
                            "members": a.get("member_scores"),
                        }
                        for a in ens
                    ],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.caption("None")

            other = result.get("other_anomalies") or []
            if other:
                st.markdown("#### Other anomalies")
                st.dataframe(other, use_container_width=True, hide_index=True)

    with st.expander("Latest window table"):
        df_all = series_frame(tail, signals[0] if signals else "")
        st.dataframe(df_all, use_container_width=True)


if __name__ == "__main__":
    main()
