/** History buffer helpers for scrubbing Stage 6 telemetry ticks. */

import { AnomalyEvent } from "./overlays";

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

/** Append a tick, de-dupe by tick_index when present, cap length. */
export function appendTick(history: TickEvent[], event: TickEvent): TickEvent[] {
  const next = [...history];
  if (typeof event.tick_index === "number") {
    const idx = next.findIndex((e) => e.tick_index === event.tick_index);
    if (idx >= 0) {
      next[idx] = event;
      return next.length > MAX_HISTORY ? next.slice(-MAX_HISTORY) : next;
    }
  }
  next.push(event);
  return next.length > MAX_HISTORY ? next.slice(-MAX_HISTORY) : next;
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
    if (ev.powerflow?.ran !== true) return;
    const atMs = tickTimeMs(ev) ?? index;
    const tick = ev.tick_index ?? index;
    out.push({
      kind: "tick",
      index,
      atMs,
      label: `tick ${tick}`,
      ran: true,
      converged: ev.powerflow.converged ?? null,
    });
  });
  return out;
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
  if (history.length <= 1) return 0;
  const times = history.map((e, i) => tickTimeMs(e) ?? i);
  const min = Math.min(...times);
  const max = Math.max(...times);
  if (max === min) return marker.index >= 0 ? marker.index / (history.length - 1) : 1;
  const t = marker.atMs;
  return Math.max(0, Math.min(1, (t - min) / (max - min)));
}
