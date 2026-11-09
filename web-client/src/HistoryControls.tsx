import {
  AnomalyMarker,
  PowerflowMarker,
  TickEvent,
  historyTimeLabel,
  markerFraction,
  nextAnomalyIndex,
  nextPowerflowIndex,
  playheadFraction,
  prevAnomalyIndex,
  prevPowerflowIndex,
  timedMarkerFraction,
} from "./history";

type Props = {
  history: TickEvent[];
  selectedIndex: number;
  followLive: boolean;
  /** When false, Follow live stays disabled (simulator stopped). */
  liveFollowAllowed: boolean;
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
  liveFollowAllowed,
  markers,
  anomalyMarkers,
  onSelectIndex,
  onFollowLive,
}: Props) {
  const selected = history[selectedIndex];
  const label = historyTimeLabel(selected, selectedIndex);
  const max = Math.max(0, history.length - 1);
  const prevAnom = prevAnomalyIndex(history, selectedIndex);
  const nextAnom = nextAnomalyIndex(history, selectedIndex);
  const prevPf = prevPowerflowIndex(history, selectedIndex);
  const nextPf = nextPowerflowIndex(history, selectedIndex);
  const pfTickCount = markers.filter((m) => m.kind === "tick").length;
  const pfManualCount = markers.filter((m) => m.kind === "manual").length;
  const playhead = `${playheadFraction(history, selectedIndex) * 100}%`;

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
          disabled={prevAnom === null}
          onClick={() => prevAnom !== null && onSelectIndex(prevAnom)}
          aria-label="Previous anomaly"
        >
          Prev anomaly
        </button>
        <button
          type="button"
          className="ghost"
          disabled={nextAnom === null}
          onClick={() => nextAnom !== null && onSelectIndex(nextAnom)}
          aria-label="Next anomaly"
        >
          Next anomaly
        </button>
        <button
          type="button"
          className="ghost"
          disabled={prevPf === null}
          onClick={() => prevPf !== null && onSelectIndex(prevPf)}
          aria-label="Previous powerflow"
        >
          Prev powerflow
        </button>
        <button
          type="button"
          className="ghost"
          disabled={nextPf === null}
          onClick={() => nextPf !== null && onSelectIndex(nextPf)}
          aria-label="Next powerflow"
        >
          Next powerflow
        </button>
        <button
          type="button"
          className="ghost"
          disabled={!liveFollowAllowed || followLive}
          onClick={onFollowLive}
          title={liveFollowAllowed ? undefined : "Start the simulator to follow live"}
        >
          {followLive ? "Live" : "Follow live"}
        </button>
        <span className="history-label">{label}</span>
      </div>

      <div className="timeline-stack" aria-label="History timeline">
        <div className="timeline-rail">
          <div className="timeline-rail-label">Anomalies</div>
          <div className="pf-timeline-track anom-track">
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
              <div className="pf-playhead" style={{ left: playhead }} aria-hidden />
            ) : null}
          </div>
        </div>

        <div className="timeline-rail">
          <div className="timeline-rail-label">Powerflow</div>
          <div className="pf-timeline-track pf-track" data-testid="powerflow-track">
            {markers.map((m, i) => {
              const left = `${markerFraction(m, history) * 100}%`;
              const title =
                m.kind === "manual" ? `${m.label} (manual powerflow)` : m.label;
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
            {history.length > 0 ? (
              <div className="pf-playhead" style={{ left: playhead }} aria-hidden />
            ) : null}
          </div>
        </div>

        <div className="pf-timeline-caption">
          Anomalies · {anomalyMarkers.length}
          {pfTickCount ? ` · powerflow · ${pfTickCount}` : ""}
          {pfManualCount ? ` · manual · ${pfManualCount}` : ""}
        </div>
      </div>
    </div>
  );
}
