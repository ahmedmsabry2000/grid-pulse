import { PowerflowMarker, TickEvent, markerFraction, tickTimestamp } from "./history";

type Props = {
  history: TickEvent[];
  selectedIndex: number;
  followLive: boolean;
  markers: PowerflowMarker[];
  onSelectIndex: (index: number) => void;
  onFollowLive: () => void;
};

export default function HistoryControls({
  history,
  selectedIndex,
  followLive,
  markers,
  onSelectIndex,
  onFollowLive,
}: Props) {
  const selected = history[selectedIndex];
  const label = selected
    ? `tick ${selected.tick_index ?? selectedIndex} · ${tickTimestamp(selected) ?? "—"}`
    : "no history yet";
  const max = Math.max(0, history.length - 1);

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
        <button type="button" className="ghost" disabled={followLive} onClick={onFollowLive}>
          {followLive ? "Live" : "Follow live"}
        </button>
        <span className="history-label">{label}</span>
      </div>
      <div className="pf-timeline" aria-label="Powerflow timeline">
        <div className="pf-timeline-track">
          {markers.map((m, i) => {
            const left = `${markerFraction(m, history) * 100}%`;
            const title =
              m.kind === "manual"
                ? `${m.label} (manual)`
                : `${m.label} · pf ran${m.converged === false ? " (not converged)" : m.converged ? " (ok)" : ""}`;
            return (
              <button
                key={`${m.kind}-${m.index}-${m.atMs}-${i}`}
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
            <div
              className="pf-playhead"
              style={{ left: `${max === 0 ? 0 : (selectedIndex / max) * 100}%` }}
              aria-hidden
            />
          ) : null}
        </div>
        <div className="pf-timeline-caption">
          Powerflow runs · {markers.filter((m) => m.kind === "tick").length} ticks
          {markers.some((m) => m.kind === "manual")
            ? ` · ${markers.filter((m) => m.kind === "manual").length} manual`
            : ""}
        </div>
      </div>
    </div>
  );
}
