import { useEffect, useMemo, useRef, useState } from "react";
import {
  PowerflowResult,
  Topology,
  fetchEvents,
  fetchNetworks,
  fetchTopology,
  postPowerflow,
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
        <div className="legend" aria-label="overlay legend">
          <span className="lg lg-meas">meas</span>
          <span className="lg lg-pf">pf</span>
          <span className="lg lg-rate">rating</span>
        </div>
        <div className="status">
          WS: {wsState} · hist {history.length} · overlays {overlays.length}
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
          {selected ? (
            <pre>
              {JSON.stringify(
                {
                  tick_index: selected.tick_index,
                  time: selected.measurements?.[0]?.timestamp ?? null,
                  gate: selected.gate,
                  powerflow: selected.powerflow,
                  anomaly_count: Array.isArray(selected.anomalies)
                    ? selected.anomalies.length
                    : 0,
                },
                null,
                2,
              )}
            </pre>
          ) : (
            <p className="status">Waiting for telemetry…</p>
          )}
          <h3>Anomalies at selection</h3>
          <pre>{JSON.stringify(selected?.anomalies ?? [], null, 2)}</pre>
          <h3>Gate / powerflow (on-demand)</h3>
          {pf ? (
            <pre>
              {JSON.stringify(
                {
                  gate: pf.gate,
                  powerflow: pf.powerflow,
                  ok: pf.ok,
                  error: pf.error,
                },
                null,
                2,
              )}
            </pre>
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
