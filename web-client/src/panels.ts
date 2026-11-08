/** Operator-facing panel formatters — never emit raw JSON blobs. */

import { PowerflowResult } from "./api";
import { TickEvent, tickTimestamp } from "./history";
import {
  AnomalyEvent,
  OverlayKind,
  busIdFromSignal,
  classifyAnomaly,
  elementIdsFromSignal,
} from "./overlays";

export type AnomalyRow = {
  badge: "meas" | "pf" | "rating" | "other";
  kind: OverlayKind | "other";
  type: string;
  asset: string;
  score: string;
  reason: string;
};

export type RatingRow = {
  asset: string;
  quantity: string;
  loading: string;
  limit: string;
  margin: string;
};

export type EnsembleRow = {
  asset: string;
  score: string;
  reason: string;
  members: string;
};

export type PowerflowSummary = {
  gate: string;
  status: string;
};

const BADGE_FOR_KIND: Record<OverlayKind, AnomalyRow["badge"]> = {
  measurement: "meas",
  pf_output: "pf",
  rating: "rating",
};

function fmtNum(value: unknown, digits = 2): string {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value.toFixed(digits);
  }
  if (typeof value === "string" && value.trim()) return value;
  return "—";
}

/** Human asset label from Stage 6 signal_id (bus_N / line:N / trafo:N). */
export function assetLabelFromSignal(signalId: string | undefined): string {
  if (!signalId) return "—";
  const bus = busIdFromSignal(signalId);
  if (bus !== undefined) return `bus ${bus + 1}`;
  const { lineId, trafoId } = elementIdsFromSignal(signalId);
  if (lineId !== undefined) return `line ${lineId}`;
  if (trafoId !== undefined) return `trafo ${trafoId}`;
  return signalId;
}

export function formatTickSummary(
  tick: TickEvent | null,
  networkId: string,
): string {
  if (!tick) return "Waiting for telemetry…";
  const time = tickTimestamp(tick) ?? "unknown time";
  const tickId =
    typeof tick.tick_index === "number" ? `tick ${tick.tick_index}` : "tick —";
  const gate = tick.gate?.action ?? "gate —";
  let pf = "pf —";
  if (tick.powerflow?.ran === true) {
    pf =
      tick.powerflow.converged === true
        ? "pf ok"
        : tick.powerflow.converged === false
          ? "pf failed"
          : "pf ran";
  } else if (tick.powerflow?.ran === false) {
    pf = "pf skipped";
  }
  const n = Array.isArray(tick.anomalies) ? tick.anomalies.length : 0;
  const anom = n === 1 ? "1 anomaly" : `${n} anomalies`;
  return `${time} · ${tickId} · ${networkId} · ${gate} · ${pf} · ${anom}`;
}

export function formatAnomalyRows(
  anomalies: AnomalyEvent[] | undefined | null,
): AnomalyRow[] {
  if (!Array.isArray(anomalies)) return [];
  return anomalies.map((a) => {
    const kind = classifyAnomaly(a.type) ?? "other";
    const badge = kind === "other" ? "other" : BADGE_FOR_KIND[kind];
    return {
      badge,
      kind,
      type: a.type,
      asset: assetLabelFromSignal(a.signal_id),
      score: fmtNum(a.score),
      reason: (a.detail && String(a.detail)) || a.quantity || a.type,
    };
  });
}

export function formatPowerflowSummary(
  pf: PowerflowResult | null | undefined,
): PowerflowSummary {
  if (!pf) {
    return { gate: "—", status: "Run powerflow to populate." };
  }
  const action = String((pf.gate as { action?: string } | null)?.action ?? "—");
  const reason = (pf.gate as { reason?: string | null } | null)?.reason;
  const gate = reason ? `${action} (${reason})` : action;
  if (pf.error) {
    return { gate, status: String(pf.error) };
  }
  const actionLower = action.toLowerCase();
  if (actionLower === "skip") {
    return { gate, status: "Powerflow skipped by quality gate." };
  }
  const power = pf.powerflow as {
    ran?: boolean;
    converged?: boolean | null;
    error?: string | null;
  } | null;
  if (power?.ran && power.converged === true) {
    return { gate, status: "Powerflow converged." };
  }
  if (power?.ran && power.converged === false) {
    return {
      gate,
      status: power.error
        ? `Powerflow did not converge: ${power.error}`
        : "Powerflow did not converge.",
    };
  }
  if (power?.ran) {
    return { gate, status: "Powerflow ran." };
  }
  return { gate, status: pf.ok ? "Ready." : "Powerflow failed." };
}

export function formatRatingRows(
  ratings: Array<Record<string, unknown>> | undefined | null,
): RatingRow[] {
  if (!Array.isArray(ratings)) return [];
  const rows = ratings.map((a) => {
    const margin =
      typeof a.margin === "number" && Number.isFinite(a.margin) ? a.margin : null;
    return {
      asset: assetLabelFromSignal(
        typeof a.signal_id === "string" ? a.signal_id : undefined,
      ),
      quantity: typeof a.quantity === "string" ? a.quantity : "—",
      loading: fmtNum(a.value),
      limit: fmtNum(a.limit),
      margin: margin === null ? "—" : String(margin),
      _sort: margin ?? Number.POSITIVE_INFINITY,
    };
  });
  rows.sort((a, b) => a._sort - b._sort);
  return rows.map(({ _sort: _, ...rest }) => rest);
}

function flattenMemberScores(raw: unknown): string {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return "—";
  const entries = Object.entries(raw as Record<string, unknown>)
    .map(([k, v]) => `${k}=${fmtNum(v)}`)
    .sort();
  return entries.length ? entries.join(", ") : "—";
}

export function formatEnsembleRows(
  anomalies: Array<Record<string, unknown>> | undefined | null,
): EnsembleRow[] {
  if (!Array.isArray(anomalies)) return [];
  return anomalies.map((a) => ({
    asset: assetLabelFromSignal(
      typeof a.signal_id === "string" ? a.signal_id : undefined,
    ),
    score: fmtNum(a.score),
    reason: typeof a.detail === "string" && a.detail ? a.detail : "ensemble",
    members: flattenMemberScores(a.member_scores),
  }));
}
