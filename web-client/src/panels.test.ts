import { describe, expect, it } from "vitest";
import {
  formatAnomalyRows,
  formatEnsembleRows,
  formatPowerflowSummary,
  formatRatingRows,
  formatTickSummary,
} from "./panels";
import { TickEvent } from "./history";
import { AnomalyEvent } from "./overlays";
import { PowerflowResult } from "./api";

describe("formatTickSummary", () => {
  it("renders a one-line operator summary without JSON braces", () => {
    const tick: TickEvent = {
      tick_index: 7,
      gate: { action: "run", reason: null },
      powerflow: { ran: true, converged: true },
      anomalies: [{ type: "measurement_spike", signal_id: "bus_1_vm_pu", score: 0.9 }],
      measurements: [{ timestamp: "2026-01-01T12:00:00Z", signal_id: "bus_1_vm_pu", value: 1.0 }],
    };
    const line = formatTickSummary(tick, "case14");
    expect(line).toContain("tick 7");
    expect(line).toContain("case14");
    expect(line).toContain("2026-01-01T12:00:00Z");
    expect(line).toMatch(/1 anomal/i);
    expect(line).not.toMatch(/[{}]/);
  });

  it("handles empty selection", () => {
    expect(formatTickSummary(null, "case14")).toBe("Waiting for telemetry…");
  });
});

describe("formatAnomalyRows", () => {
  it("maps anomalies to badge rows using overlay classifiers", () => {
    const anomalies: AnomalyEvent[] = [
      {
        type: "measurement_spike",
        signal_id: "bus_3_vm_pu",
        score: 0.88,
        detail: "spike",
      },
      {
        type: "rating_exceedance",
        signal_id: "line:2",
        score: 1,
        quantity: "loading_percent",
        detail: "over limit",
      },
    ];
    const rows = formatAnomalyRows(anomalies);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({
      badge: "meas",
      asset: "bus 3",
      score: "0.88",
      reason: "spike",
    });
    expect(rows[1]).toMatchObject({
      badge: "rating",
      asset: "line 2",
      reason: "over limit",
    });
    expect(JSON.stringify(rows)).not.toMatch(/member_scores/);
  });

  it("returns empty list for missing anomalies", () => {
    expect(formatAnomalyRows(undefined)).toEqual([]);
  });
});

describe("formatPowerflowSummary", () => {
  it("summarizes gate and PF status in plain text", () => {
    const pf: PowerflowResult = {
      ok: true,
      error: null,
      gate: { action: "run", reason: null },
      powerflow: { ran: true, converged: true, error: null },
      rating_exceedances: [],
      ensemble_anomalies: [],
      other_anomalies: [],
    };
    const summary = formatPowerflowSummary(pf);
    expect(summary.status).toMatch(/converged/i);
    expect(summary.gate).toMatch(/run/i);
    expect(summary.status).not.toMatch(/[{}]/);
  });

  it("surfaces skip and failure plainly", () => {
    const skipped = formatPowerflowSummary({
      ok: true,
      error: null,
      gate: { action: "skip", reason: "bad quality" },
      powerflow: { ran: false, converged: null },
      rating_exceedances: [],
      ensemble_anomalies: [],
      other_anomalies: [],
    });
    expect(skipped.status).toMatch(/skipped/i);
    expect(skipped.gate).toContain("bad quality");
  });
});

describe("formatRatingRows", () => {
  it("sorts worst loading first and flattens fields", () => {
    const rows = formatRatingRows([
      {
        type: "rating_exceedance",
        signal_id: "line:1",
        quantity: "loading_percent",
        value: 95,
        limit: 100,
        margin: 5,
      },
      {
        type: "rating_exceedance",
        signal_id: "line:4",
        quantity: "loading_percent",
        value: 120,
        limit: 100,
        margin: -20,
      },
    ]);
    expect(rows[0].asset).toBe("line 4");
    expect(rows[0].loading).toContain("120");
    expect(rows[0].margin).toBe("-20");
    expect(rows[1].asset).toBe("line 1");
  });
});

describe("formatEnsembleRows", () => {
  it("flattens member_scores into separate columns", () => {
    const rows = formatEnsembleRows([
      {
        type: "measurement_ensemble",
        signal_id: "bus_2_vm_pu",
        score: 0.7,
        detail: "ensemble hit",
        member_scores: { spike: 0.9, zscore: 0.4, iforest: 0.6 },
      },
    ]);
    expect(rows).toHaveLength(1);
    expect(rows[0].asset).toBe("bus 2");
    expect(rows[0].score).toBe("0.70");
    expect(rows[0].members).toContain("spike=0.90");
    expect(rows[0].members).toContain("zscore=0.40");
    expect(typeof rows[0].members).toBe("string");
  });
});
