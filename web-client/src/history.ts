/** History buffer helpers for scrubbing Stage 6 telemetry ticks. */

import { AnomalyEvent, classifyAnomaly } from "./overlays";

export type TickEvent = {
  tick_index?: number;
  gate?: { action?: string; reason?: string | null };
  powerflow?: { ran?: boolean; converged?: boolean | null; error?: string | null };
  anomalies?: AnomalyEvent[];
  measurements?: Array<{
    timestamp?: string;
    signal_id?: string;
    value?: number | null;
    quality?: string;
  }>;
};

export type ManualPowerflowMark = {
  id: string;
  atMs: number;
  label: string;
  ok: boolean;
};

export type PowerflowMarker = {
  kind: "tick" | "manual";
  /** Index into the history buffer for tick markers; -1 for manual. */
  index: number;
  atMs: number;
  label: string;
  ran: boolean;
  converged?: boolean | null;
};

/** Operator-facing anomaly kinds for timeline markers (legend colors). */
export type AnomalyMarkerKind = "measurement" | "pf_output" | "rating" | "ensemble";

export type AnomalyMarker = {
  index: number;
  atMs: number;
  label: string;
  kinds: AnomalyMarkerKind[];
  count: number;
};

const MAX_HISTORY = 500;

export function tickTimestamp(event: TickEvent): string | null {
  const ms = event.measurements;
  if (Array.isArray(ms) && ms.length > 0 && typeof ms[0]?.timestamp === "string") {
    return ms[0].timestamp;
  }
  return null;
}

export function tickTimeMs(event: TickEvent): number | null {
  const raw = tickTimestamp(event);
  if (!raw) return null;
  const t = Date.parse(raw);
  return Number.isFinite(t) ? t : null;
}

/** Scrubber / panel time label — never expose tick ids to operators. */
export function historyTimeLabel(
  event: TickEvent | null | undefined,
  _index: number,
): string {
  if (!event) return "no history yet";
  return tickTimestamp(event) ?? "unknown time";
}

/** True when this sample would render an orange timeline annotation. */
export function hasTimelineAnomaly(event: TickEvent): boolean {
  if (!Array.isArray(event.anomalies) || event.anomalies.length === 0) return false;
  return event.anomalies.some((a) => anomalyMarkerKind(a.type) !== null);
}

/** Map anomaly type → timeline kind (ensemble kept distinct; color ≈ meas). */
export function anomalyMarkerKind(type: string): AnomalyMarkerKind | null {
  if (type === "measurement_ensemble") return "ensemble";
  const overlay = classifyAnomaly(type);
  if (overlay === "measurement") return "measurement";
  if (overlay === "pf_output") return "pf_output";
  if (overlay === "rating") return "rating";
  return null;
}

const KIND_ORDER: AnomalyMarkerKind[] = [
  "measurement",
  "ensemble",
  "pf_output",
  "rating",
];

const KIND_SHORT: Record<AnomalyMarkerKind, string> = {
  measurement: "meas",
  ensemble: "ensemble",
  pf_output: "pf",
  rating: "rating",
};

export function anomalyMarkersFromHistory(history: TickEvent[]): AnomalyMarker[] {
  const out: AnomalyMarker[] = [];
  history.forEach((ev, index) => {
    if (!hasTimelineAnomaly(ev)) return;
    const kindSet = new Set<AnomalyMarkerKind>();
    for (const a of ev.anomalies!) {
      const k = anomalyMarkerKind(a.type);
      if (k) kindSet.add(k);
    }
    const kinds = KIND_ORDER.filter((k) => kindSet.has(k));
    const atMs = tickTimeMs(ev) ?? index;
    const time = tickTimestamp(ev) ?? "unknown time";
    const n = ev.anomalies!.length;
    const kindPart = kinds.map((k) => KIND_SHORT[k]).join("/");
    const anom = n === 1 ? "1 anomaly" : `${n} anomalies`;
    out.push({
      index,
      atMs,
      label: `${time} · ${kindPart} · ${anom}`,
      kinds,
      count: n,
    });
  });
  return out;
}

export function prevAnomalyIndex(
  history: TickEvent[],
  selectedIndex: number,
): number | null {
  for (let i = selectedIndex - 1; i >= 0; i -= 1) {
    if (hasTimelineAnomaly(history[i]!)) return i;
  }
  return null;
}

export function nextAnomalyIndex(
  history: TickEvent[],
  selectedIndex: number,
): number | null {
  for (let i = selectedIndex + 1; i < history.length; i += 1) {
    if (hasTimelineAnomaly(history[i]!)) return i;
  }
  return null;
}

function powerflowRan(event: TickEvent): boolean {
  return event.powerflow?.ran === true;
}

export function prevPowerflowIndex(
  history: TickEvent[],
  selectedIndex: number,
): number | null {
  for (let i = selectedIndex - 1; i >= 0; i -= 1) {
    if (powerflowRan(history[i]!)) return i;
  }
  return null;
}

export function nextPowerflowIndex(
  history: TickEvent[],
  selectedIndex: number,
): number | null {
  for (let i = selectedIndex + 1; i < history.length; i += 1) {
    if (powerflowRan(history[i]!)) return i;
  }
  return null;
}

export type AppendTickResult = {
  history: TickEvent[];
  /** How many samples fell off the front when the buffer capped. */
  removedFromFront: number;
};

/**
 * Append a tick, de-dupe by tick_index when present, cap length.
 * Callers must subtract ``removedFromFront`` from a scrubbed selectedIndex
 * so Prev/Next anomaly stays on the same sample as its orange marker.
 */
export function appendTickWithShift(
  history: TickEvent[],
  event: TickEvent,
): AppendTickResult {
  const next = [...history];
  if (typeof event.tick_index === "number") {
    const idx = next.findIndex((e) => e.tick_index === event.tick_index);
    if (idx >= 0) {
      next[idx] = event;
      if (next.length > MAX_HISTORY) {
        const removedFromFront = next.length - MAX_HISTORY;
        return { history: next.slice(-MAX_HISTORY), removedFromFront };
      }
      return { history: next, removedFromFront: 0 };
    }
  }
  next.push(event);
  if (next.length > MAX_HISTORY) {
    const removedFromFront = next.length - MAX_HISTORY;
    return { history: next.slice(-MAX_HISTORY), removedFromFront };
  }
  return { history: next, removedFromFront: 0 };
}

/** Append a tick, de-dupe by tick_index when present, cap length. */
export function appendTick(history: TickEvent[], event: TickEvent): TickEvent[] {
  return appendTickWithShift(history, event).history;
}

/** Keep scrub selection attached to the same sample after a front trim. */
export function shiftSelectedIndex(
  selectedIndex: number,
  removedFromFront: number,
  nextLength: number,
): number {
  if (removedFromFront <= 0) return clampIndex(selectedIndex, nextLength);
  return clampIndex(selectedIndex - removedFromFront, nextLength);
}

export function clampIndex(index: number, length: number): number {
  if (length <= 0) return 0;
  return Math.max(0, Math.min(length - 1, index));
}

export function isFollowLive(selectedIndex: number, length: number): boolean {
  if (length <= 0) return true;
  return selectedIndex >= length - 1;
}

export function powerflowMarkersFromHistory(history: TickEvent[]): PowerflowMarker[] {
  const out: PowerflowMarker[] = [];
  history.forEach((ev, index) => {
    if (!powerflowRan(ev)) return;
    const atMs = tickTimeMs(ev) ?? index;
    const time = tickTimestamp(ev) ?? "unknown time";
    const status =
      ev.powerflow?.converged === true
        ? "ok"
        : ev.powerflow?.converged === false
          ? "not converged"
          : "ran";
    out.push({
      kind: "tick",
      index,
      atMs,
      label: `${time} · powerflow ${status}`,
      ran: true,
      converged: ev.powerflow?.converged ?? null,
    });
  });
  return out;
}

/** Fraction 0..1 for any timed marker along the history span. */
export function timedMarkerFraction(
  atMs: number,
  history: TickEvent[],
  fallbackIndex = 0,
): number {
  if (history.length <= 1) return 0;
  const times = history.map((e, i) => tickTimeMs(e) ?? i);
  const min = Math.min(...times);
  const max = Math.max(...times);
  if (max === min) {
    return Math.max(0, Math.min(1, fallbackIndex / (history.length - 1)));
  }
  return Math.max(0, Math.min(1, (atMs - min) / (max - min)));
}

/** Playhead X on the timeline — same time axis as anomaly / PF markers. */
export function playheadFraction(history: TickEvent[], selectedIndex: number): number {
  if (history.length <= 1) return 0;
  const idx = clampIndex(selectedIndex, history.length);
  const ev = history[idx]!;
  const atMs = tickTimeMs(ev) ?? idx;
  return timedMarkerFraction(atMs, history, idx);
}

export function mergePowerflowMarkers(
  history: TickEvent[],
  manual: ManualPowerflowMark[],
): PowerflowMarker[] {
  const fromTicks = powerflowMarkersFromHistory(history);
  const fromManual: PowerflowMarker[] = manual.map((m) => ({
    kind: "manual",
    index: -1,
    atMs: m.atMs,
    label: m.label,
    ran: true,
    converged: m.ok ? true : false,
  }));
  return [...fromTicks, ...fromManual].sort((a, b) => a.atMs - b.atMs);
}

/** Fraction 0..1 along the history span for a marker (for timeline layout). */
export function markerFraction(
  marker: PowerflowMarker,
  history: TickEvent[],
): number {
  const fallback = marker.index >= 0 ? marker.index : history.length - 1;
  return timedMarkerFraction(marker.atMs, history, fallback);
}
