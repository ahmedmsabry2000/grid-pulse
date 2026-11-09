import {
  AnomalyMarker,
  PowerflowMarker,
  TickEvent,
  historyTimeLabel,
  markerFraction,
  nextAnomalyIndex,
  prevAnomalyIndex,
  timedMarkerFraction,
} from "./history";

type Props = {
  history: TickEvent[];
  selectedIndex: number;
  followLive: boolean;
  markers: PowerflowMarker[];
  anomalyMarkers: AnomalyMarker[];
  onSelectIndex: (index: number) => void;
  onFollowLive: () => void;
};

const KIND_CLASS: Record<string, string> = {
  measurement: "anom-meas",
  ensemble: "anom-ensemble",
  pf_output: "anom-pf",
  rating: "anom-rate",
};

export default function HistoryControls({
  history,
  selectedIndex,
  followLive,
  markers,
  anomalyMarkers,
  onSelectIndex,
  onFollowLive,
}: Props) {
  const selected = history[selectedIndex];
  const label = historyTimeLabel(selected, selectedIndex);
  const max = Math.max(0, history.length - 1);
  const prevIdx = prevAnomalyIndex(history, selectedIndex);
  const nextIdx = nextAnomalyIndex(history, selectedIndex);

  return (
    <div className="history-controls" data-testid="history-controls">
      <div className="history-row">
        <label htmlFor="history-slider">History</label>
        <input
          id="history-slider"
          type="range"
          min={0}
          max={max}
          value={history.length ? selectedIndex : 0}
          disabled={history.length === 0}
          onChange={(e) => onSelectIndex(Number(e.target.value))}
          aria-valuetext={label}
        />
        <button
          type="button"
          className="ghost"
          disabled={prevIdx === null}
          onClick={() => prevIdx !== null && onSelectIndex(prevIdx)}
          aria-label="Previous anomaly"
        >
          Prev anomaly
        </button>
        <button
          type="button"
          className="ghost"
          disabled={nextIdx === null}
          onClick={() => nextIdx !== null && onSelectIndex(nextIdx)}
          aria-label="Next anomaly"
        >
          Next anomaly
        </button>
        <button type="button" className="ghost" disabled={followLive} onClick={onFollowLive}>
          {followLive ? "Live" : "Follow live"}
        </button>
        <span className="history-label">{label}</span>
      </div>
      <div className="pf-timeline" aria-label="Anomaly timeline">
        <div className="pf-timeline-track">
          {markers.map((m, i) => {
            const left = `${markerFraction(m, history) * 100}%`;
            const title =
              m.kind === "manual"
                ? `${m.label} (manual powerflow)`
                : `${m.label} · pf ran${m.converged === false ? " (not converged)" : m.converged ? " (ok)" : ""}`;
            return (
              <button
                key={`pf-${m.kind}-${m.index}-${m.atMs}-${i}`}
                type="button"
                className={`pf-mark ${m.kind} ${m.converged === false ? "bad" : "ok"}`}
                style={{ left }}
                title={title}
                aria-label={title}
                onClick={() => {
                  if (m.kind === "tick" && m.index >= 0) onSelectIndex(m.index);
                }}
              />
            );
          })}
          {anomalyMarkers.map((m, i) => {
            const left = `${timedMarkerFraction(m.atMs, history, m.index) * 100}%`;
            const primary = m.kinds[0] ?? "measurement";
            return (
              <button
                key={`anom-${m.index}-${m.atMs}-${i}`}
                type="button"
                className={`anom-mark ${KIND_CLASS[primary] ?? "anom-meas"}`}
                style={{ left }}
                title={m.label}
                aria-label={m.label}
                data-kinds={m.kinds.join(",")}
                onClick={() => onSelectIndex(m.index)}
              />
            );
          })}
          {history.length > 0 ? (
            <div
              className="pf-playhead"
              style={{ left: `${max === 0 ? 0 : (selectedIndex / max) * 100}%` }}
              aria-hidden
            />
          ) : null}
        </div>
        <div className="pf-timeline-caption">
          Anomalies · {anomalyMarkers.length}
          {markers.length
            ? ` · powerflow runs ${markers.filter((m) => m.kind === "tick").length}`
            : ""}
          {markers.some((m) => m.kind === "manual")
            ? ` · ${markers.filter((m) => m.kind === "manual").length} manual`
            : ""}
        </div>
      </div>
    </div>
  );
}
