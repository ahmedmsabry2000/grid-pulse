import { useEffect, useMemo, useRef, useState } from "react";
import {
  PowerflowResult,
  Topology,
  fetchEvents,
  fetchNetworks,
  fetchSimulatorStatus,
  fetchTopology,
  postPowerflow,
  postSimulatorStart,
  postSimulatorStop,
  wsTelemetryUrl,
} from "./api";
import HistoryControls from "./HistoryControls";
import NetworkMap from "./NetworkMap";
import {
  ManualPowerflowMark,
  TickEvent,
  appendTick,
  clampIndex,
  isFollowLive,
  mergePowerflowMarkers,
} from "./history";
import { AnomalyEvent, OverlayHit, anomaliesToOverlayHits } from "./overlays";
import {
  formatAnomalyRows,
  formatEnsembleRows,
  formatPowerflowSummary,
  formatRatingRows,
  formatTickSummary,
} from "./panels";

export default function App() {
  const [networks, setNetworks] = useState<string[]>([]);
  const [networkId, setNetworkId] = useState("case14");
  const [topology, setTopology] = useState<Topology | null>(null);
  const [pf, setPf] = useState<PowerflowResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wsState, setWsState] = useState("connecting");
  const [history, setHistory] = useState<TickEvent[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [followLive, setFollowLive] = useState(true);
  const [manualMarks, setManualMarks] = useState<ManualPowerflowMark[]>([]);
  const [simStatus, setSimStatus] = useState<"running" | "stopped">("stopped");
  const [simBusy, setSimBusy] = useState(false);
  const followLiveRef = useRef(followLive);
  followLiveRef.current = followLive;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const nets = await fetchNetworks();
        if (cancelled) return;
        setNetworks(nets);
        if (nets.length && !nets.includes(networkId)) {
          setNetworkId(nets[0]);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setTopology(null);
    (async () => {
      try {
        const topo = await fetchTopology(networkId);
        if (!cancelled) setTopology(topo);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [networkId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const rows = (await fetchEvents(500)) as TickEvent[];
        if (cancelled || !rows.length) return;
        setHistory((prev) => {
          let next = prev;
          for (const ev of rows) next = appendTick(next, ev);
          return next;
        });
        if (followLiveRef.current) {
          setSelectedIndex(Math.max(0, rows.length - 1));
        }
      } catch {
        /* WS catch-up still works if REST history fails */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const st = await fetchSimulatorStatus();
        if (!cancelled) setSimStatus(st.status);
      } catch {
        /* toolbar stays Stopped until operator acts */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const url = wsTelemetryUrl();
    const ws = new WebSocket(url);
    setWsState("connecting");
    ws.onopen = () => setWsState("live");
    ws.onclose = () => setWsState("closed");
    ws.onerror = () => setWsState("error");
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(String(ev.data)) as {
          type: string;
          event?: TickEvent;
        };
        if (msg.type === "telemetry" && msg.event) {
          setHistory((prev) => {
            const next = appendTick(prev, msg.event as TickEvent);
            if (followLiveRef.current) {
              setSelectedIndex(next.length - 1);
            }
            return next;
          });
        }
      } catch {
        /* ignore malformed */
      }
    };
    return () => ws.close();
  }, []);

  const selected = history[clampIndex(selectedIndex, history.length)] ?? null;

  const overlays: OverlayHit[] = useMemo(() => {
    const fromTick = anomaliesToOverlayHits(
      Array.isArray(selected?.anomalies) ? selected!.anomalies! : [],
    );
    if (!pf || !followLive) return fromTick;
    const fromPf = anomaliesToOverlayHits([
      ...pf.rating_exceedances,
      ...pf.ensemble_anomalies,
      ...pf.other_anomalies,
    ] as AnomalyEvent[]);
    return [...fromTick, ...fromPf];
  }, [selected, pf, followLive]);

  const markers = useMemo(
    () => mergePowerflowMarkers(history, manualMarks),
    [history, manualMarks],
  );

  const tickSummary = formatTickSummary(selected, networkId);
  const anomalyRows = formatAnomalyRows(
    Array.isArray(selected?.anomalies) ? selected!.anomalies : [],
  );
  const pfSummary = formatPowerflowSummary(pf);
  const ratingRows = formatRatingRows(pf?.rating_exceedances);
  const ensembleRows = formatEnsembleRows(pf?.ensemble_anomalies);

  function onSelectIndex(index: number) {
    const clamped = clampIndex(index, history.length);
    setSelectedIndex(clamped);
    setFollowLive(isFollowLive(clamped, history.length));
  }

  function onFollowLive() {
    setFollowLive(true);
    if (history.length) setSelectedIndex(history.length - 1);
  }

  async function onRunPowerflow() {
    setBusy(true);
    setError(null);
    try {
      const result = await postPowerflow(networkId);
      setPf(result);
      const converged = (result.powerflow as { converged?: boolean } | null)?.converged;
      setManualMarks((prev) => [
        ...prev,
        {
          id: `manual-${Date.now()}`,
          atMs: Date.now(),
          label: "Run powerflow",
          ok: Boolean(result.ok && converged !== false),
        },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onToggleSimulator() {
    setSimBusy(true);
    setError(null);
    try {
      const next =
        simStatus === "running" ? await postSimulatorStop() : await postSimulatorStart();
      setSimStatus(next.status);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSimBusy(false);
    }
  }

  return (
    <div className="app">
      <header className="toolbar">
        <div className="brand">Grid Pulse</div>
        <label htmlFor="network">Network</label>
        <select
          id="network"
          value={networkId}
          onChange={(e) => setNetworkId(e.target.value)}
        >
          {(networks.length ? networks : [networkId]).map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
        <button type="button" disabled={busy} onClick={onRunPowerflow}>
          {busy ? "Running…" : "Run powerflow"}
        </button>
        <button
          type="button"
          className="ghost sim-toggle"
          disabled={simBusy}
          onClick={onToggleSimulator}
          aria-pressed={simStatus === "running"}
        >
          Simulator: {simBusy ? "…" : simStatus === "running" ? "Running" : "Stopped"}
        </button>
        <div className="legend" aria-label="overlay legend">
          <span className="lg lg-meas">meas</span>
          <span className="lg lg-pf">pf</span>
          <span className="lg lg-rate">rating</span>
        </div>
        <div className="status">
          WS: {wsState} · sim {simStatus} · hist {history.length} · overlays{" "}
          {overlays.length}
        </div>
      </header>
      <HistoryControls
        history={history}
        selectedIndex={clampIndex(selectedIndex, history.length)}
        followLive={followLive}
        markers={markers}
        onSelectIndex={onSelectIndex}
        onFollowLive={onFollowLive}
      />
      <div className="main">
        <div className="map-pane">
          <NetworkMap topology={topology} overlays={overlays} />
        </div>
        <aside className="panel">
          <h2>Panels</h2>
          {error ? <p className="err">{error}</p> : null}
          <h3>Selected tick</h3>
          <p className="summary-line">{tickSummary}</p>
          <h3>Anomalies at selection</h3>
          {anomalyRows.length ? (
            <table className="op-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Asset</th>
                  <th>Score</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {anomalyRows.map((row, i) => (
                  <tr key={`${row.type}-${row.asset}-${i}`}>
                    <td>
                      <span className={`lg lg-${row.badge === "rating" ? "rate" : row.badge}`}>
                        {row.badge}
                      </span>
                    </td>
                    <td>{row.asset}</td>
                    <td>{row.score}</td>
                    <td>{row.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="status">None</p>
          )}
          <h3>Gate / powerflow (on-demand)</h3>
          {pf ? (
            <div className="pf-summary">
              <p className="summary-line">Gate: {pfSummary.gate}</p>
              <p className="summary-line">{pfSummary.status}</p>
            </div>
          ) : (
            <p className="status">Run powerflow to populate.</p>
          )}
          <h3>Rating exceedances</h3>
          {ratingRows.length ? (
            <table className="op-table">
              <thead>
                <tr>
                  <th>Asset</th>
                  <th>Qty</th>
                  <th>Value</th>
                  <th>Limit</th>
                  <th>Margin</th>
                </tr>
              </thead>
              <tbody>
                {ratingRows.map((row, i) => (
                  <tr key={`${row.asset}-${i}`}>
                    <td>{row.asset}</td>
                    <td>{row.quantity}</td>
                    <td>{row.loading}</td>
                    <td>{row.limit}</td>
                    <td>{row.margin}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="status">None</p>
          )}
          <h3>Ensemble anomalies</h3>
          {ensembleRows.length ? (
            <table className="op-table">
              <thead>
                <tr>
                  <th>Asset</th>
                  <th>Score</th>
                  <th>Members</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {ensembleRows.map((row, i) => (
                  <tr key={`${row.asset}-${i}`}>
                    <td>{row.asset}</td>
                    <td>{row.score}</td>
                    <td>{row.members}</td>
                    <td>{row.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="status">None</p>
          )}
        </aside>
      </div>
    </div>
  );
}
