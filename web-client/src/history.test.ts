import { describe, expect, it } from "vitest";
import {
  anomalyMarkersFromHistory,
  appendTick,
  clampIndex,
  historyTimeLabel,
  isFollowLive,
  markerFraction,
  mergePowerflowMarkers,
  nextAnomalyIndex,
  powerflowMarkersFromHistory,
  prevAnomalyIndex,
  tickTimeMs,
  tickTimestamp,
} from "./history";

const t0 = {
  tick_index: 0,
  measurements: [{ timestamp: "2026-01-01T00:00:00Z", signal_id: "bus_1_vm_pu", value: 1 }],
  powerflow: { ran: true, converged: true },
  anomalies: [],
};
const t1 = {
  tick_index: 1,
  measurements: [{ timestamp: "2026-01-01T00:01:00Z", signal_id: "bus_1_vm_pu", value: 1 }],
  powerflow: { ran: false, converged: null },
  anomalies: [{ type: "measurement_spike", signal_id: "bus_1_vm_pu" }],
};
const t2 = {
  tick_index: 2,
  measurements: [{ timestamp: "2026-01-01T00:02:00Z", signal_id: "bus_1_vm_pu", value: 1 }],
  powerflow: { ran: true, converged: false },
  anomalies: [],
};
const t3 = {
  tick_index: 3,
  measurements: [{ timestamp: "2026-01-01T00:03:00Z", signal_id: "bus_1_vm_pu", value: 1 }],
  powerflow: { ran: true, converged: true },
  anomalies: [
    { type: "rating_exceedance", signal_id: "line:1" },
    { type: "measurement_ensemble", signal_id: "bus_2_vm_pu" },
  ],
};
const t4 = {
  tick_index: 4,
  measurements: [{ timestamp: "2026-01-01T00:04:00Z", signal_id: "bus_1_vm_pu", value: 1 }],
  powerflow: { ran: false, converged: null },
  anomalies: [{ type: "pf_residual", signal_id: "bus_3_vm_pu" }],
};

describe("tickTimestamp / tickTimeMs", () => {
  it("reads first measurement timestamp", () => {
    expect(tickTimestamp(t0)).toBe("2026-01-01T00:00:00Z");
    expect(tickTimeMs(t0)).toBe(Date.parse("2026-01-01T00:00:00Z"));
  });
});

describe("appendTick", () => {
  it("appends and dedupes by tick_index", () => {
    let h = appendTick([], t0);
    h = appendTick(h, t1);
    expect(h).toHaveLength(2);
    h = appendTick(h, { ...t1, anomalies: [] });
    expect(h).toHaveLength(2);
    expect(h[1].anomalies).toEqual([]);
  });
});

describe("clampIndex / isFollowLive", () => {
  it("clamps and detects live end", () => {
    expect(clampIndex(99, 3)).toBe(2);
    expect(isFollowLive(2, 3)).toBe(true);
    expect(isFollowLive(1, 3)).toBe(false);
  });
});

describe("powerflowMarkersFromHistory", () => {
  it("only includes ticks where powerflow ran", () => {
    const marks = powerflowMarkersFromHistory([t0, t1, t2]);
    expect(marks).toHaveLength(2);
    expect(marks.map((m) => m.index)).toEqual([0, 2]);
    expect(marks[1].converged).toBe(false);
  });

  it("labels powerflow markers by time, not tick id", () => {
    const marks = powerflowMarkersFromHistory([t0, t1, t2]);
    expect(marks[0].label).toContain("2026-01-01T00:00:00Z");
    expect(marks[0].label).not.toMatch(/tick\s*\d/i);
  });
});

describe("mergePowerflowMarkers", () => {
  it("merges manual marks sorted by time", () => {
    const marks = mergePowerflowMarkers([t0, t1, t2], [
      { id: "m1", atMs: Date.parse("2026-01-01T00:01:30Z"), label: "manual", ok: true },
    ]);
    expect(marks).toHaveLength(3);
    expect(marks[1].kind).toBe("manual");
  });
});

describe("markerFraction", () => {
  it("places markers along the time span", () => {
    const hist = [t0, t1, t2];
    const marks = powerflowMarkersFromHistory(hist);
    expect(markerFraction(marks[0], hist)).toBe(0);
    expect(markerFraction(marks[1], hist)).toBe(1);
  });
});

describe("historyTimeLabel", () => {
  it("shows selection time without tick ids", () => {
    expect(historyTimeLabel(t1, 1)).toBe("2026-01-01T00:01:00Z");
    expect(historyTimeLabel(t1, 1)).not.toMatch(/tick/i);
  });

  it("falls back when empty", () => {
    expect(historyTimeLabel(undefined, 0)).toBe("no history yet");
  });
});

describe("anomalyMarkersFromHistory", () => {
  it("emits one marker per anomalous sample with legend kinds", () => {
    const marks = anomalyMarkersFromHistory([t0, t1, t2, t3, t4]);
    expect(marks.map((m) => m.index)).toEqual([1, 3, 4]);
    expect(marks[0]).toMatchObject({
      kinds: ["measurement"],
      label: expect.stringContaining("2026-01-01T00:01:00Z"),
    });
    expect(marks[1].kinds).toEqual(expect.arrayContaining(["rating", "ensemble"]));
    expect(marks[2].kinds).toEqual(["pf_output"]);
    for (const m of marks) {
      expect(m.label).not.toMatch(/tick\s*\d/i);
    }
  });

  it("skips empty anomaly lists", () => {
    expect(anomalyMarkersFromHistory([t0, t2])).toEqual([]);
  });
});

describe("prevAnomalyIndex / nextAnomalyIndex", () => {
  const hist = [t0, t1, t2, t3, t4];

  it("jumps to previous / next anomalous indices", () => {
    expect(prevAnomalyIndex(hist, 4)).toBe(3);
    expect(prevAnomalyIndex(hist, 3)).toBe(1);
    expect(prevAnomalyIndex(hist, 1)).toBe(null);
    expect(nextAnomalyIndex(hist, 0)).toBe(1);
    expect(nextAnomalyIndex(hist, 1)).toBe(3);
    expect(nextAnomalyIndex(hist, 4)).toBe(null);
  });

  it("returns null when no anomalies exist", () => {
    expect(prevAnomalyIndex([t0, t2], 1)).toBe(null);
    expect(nextAnomalyIndex([t0, t2], 0)).toBe(null);
  });
});
