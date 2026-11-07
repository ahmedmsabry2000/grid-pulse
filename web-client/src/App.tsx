import { useEffect, useState } from "react";
import {
  PowerflowResult,
  Topology,
  fetchNetworks,
  fetchTopology,
  postPowerflow,
  wsTelemetryUrl,
} from "./api";
import NetworkMap from "./NetworkMap";

type TickSummary = {
  tick_index?: number;
  anomaly_count: number;
};

export default function App() {
  const [networks, setNetworks] = useState<string[]>([]);
  const [networkId, setNetworkId] = useState("case14");
  const [topology, setTopology] = useState<Topology | null>(null);
  const [pf, setPf] = useState<PowerflowResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wsState, setWsState] = useState("connecting");
  const [ticks, setTicks] = useState<TickSummary[]>([]);

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
          event?: { tick_index?: number; anomalies?: unknown[] };
        };
        if (msg.type === "telemetry" && msg.event) {
          const summary: TickSummary = {
            tick_index: msg.event.tick_index,
            anomaly_count: Array.isArray(msg.event.anomalies)
              ? msg.event.anomalies.length
              : 0,
          };
          setTicks((prev) => [...prev.slice(-49), summary]);
        }
      } catch {
        /* ignore malformed */
      }
    };
    return () => ws.close();
  }, []);

  async function onRunPowerflow() {
    setBusy(true);
    setError(null);
    try {
      const result = await postPowerflow(networkId);
      setPf(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
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
        <div className="status">WS: {wsState}</div>
      </header>
      <div className="main">
        <div className="map-pane">
          <NetworkMap topology={topology} />
        </div>
        <aside className="panel">
          <h2>Panels</h2>
          {error ? <p className="err">{error}</p> : null}
          <h3>Live ticks</h3>
          <ul className="tick-list">
            {ticks.length === 0 ? <li>Waiting for telemetry…</li> : null}
            {[...ticks].reverse().map((t, i) => (
              <li key={`${t.tick_index}-${i}`}>
                tick {t.tick_index ?? "?"} · anomalies {t.anomaly_count}
              </li>
            ))}
          </ul>
          <h3>Gate / powerflow</h3>
          {pf ? (
            <pre>{JSON.stringify({ gate: pf.gate, powerflow: pf.powerflow, ok: pf.ok, error: pf.error }, null, 2)}</pre>
          ) : (
            <p className="status">Run powerflow to populate.</p>
          )}
          <h3>Rating exceedances</h3>
          <pre>{JSON.stringify(pf?.rating_exceedances ?? [], null, 2)}</pre>
          <h3>Ensemble anomalies</h3>
          <pre>{JSON.stringify(pf?.ensemble_anomalies ?? [], null, 2)}</pre>
        </aside>
      </div>
    </div>
  );
}
