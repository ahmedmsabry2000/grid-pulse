import { describe, expect, it } from "vitest";
import {
  appendTick,
  clampIndex,
  isFollowLive,
  markerFraction,
  mergePowerflowMarkers,
  powerflowMarkersFromHistory,
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
