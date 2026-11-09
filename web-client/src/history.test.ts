import { describe, expect, it } from "vitest";
import {
  anomalyMarkersFromHistory,
  appendTick,
  appendTickWithShift,
  clampIndex,
  historyTimeLabel,
  indexFromTimelineFraction,
  isFollowLive,
  markerFraction,
  mergePowerflowMarkers,
  nextAnomalyIndex,
  nextPowerflowIndex,
  playheadFraction,
  powerflowMarkersFromHistory,
  prevAnomalyIndex,
  prevPowerflowIndex,
  shiftSelectedIndex,
  shouldAdvanceFollowLive,
  shouldIngestLiveTelemetry,
  sortHistoryByTime,
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

describe("appendTickWithShift / shiftSelectedIndex", () => {
  it("reports front removals when the buffer caps so scrub stays on the same sample", () => {
    const seed = Array.from({ length: 500 }, (_, i) => ({
      tick_index: i,
      measurements: [
        {
          timestamp: `2026-01-01T00:${String(Math.floor(i / 60)).padStart(2, "0")}:${String(i % 60).padStart(2, "0")}Z`,
          signal_id: "bus_1_vm_pu",
          value: 1,
        },
      ],
      anomalies:
        i === 498
          ? [{ type: "measurement_spike", signal_id: "bus_1_vm_pu" }]
          : [],
    }));
    const selectedBefore = 498;
    const incoming = {
      tick_index: 500,
      measurements: [
        { timestamp: "2026-01-01T00:08:20Z", signal_id: "bus_1_vm_pu", value: 1 },
      ],
      anomalies: [],
    };
    const { history, removedFromFront } = appendTickWithShift(seed, incoming);
    expect(removedFromFront).toBe(1);
    expect(history).toHaveLength(500);
    const selectedAfter = shiftSelectedIndex(selectedBefore, removedFromFront, history.length);
    expect(selectedAfter).toBe(497);
    expect(history[selectedAfter]?.tick_index).toBe(498);
    expect(prevAnomalyIndex(history, selectedAfter + 1)).toBe(selectedAfter);
  });
});

describe("clampIndex / isFollowLive", () => {
  it("clamps and detects live end", () => {
    expect(clampIndex(99, 3)).toBe(2);
    expect(isFollowLive(2, 3)).toBe(true);
    expect(isFollowLive(1, 3)).toBe(false);
  });
});

describe("shouldIngestLiveTelemetry / shouldAdvanceFollowLive", () => {
  it("freezes ingest and follow-live while simulator is stopped", () => {
    expect(shouldIngestLiveTelemetry("stopped")).toBe(false);
    expect(shouldAdvanceFollowLive("stopped", true)).toBe(false);
    expect(shouldAdvanceFollowLive("stopped", false)).toBe(false);
  });

  it("allows ingest while running; follow-live only when enabled", () => {
    expect(shouldIngestLiveTelemetry("running")).toBe(true);
    expect(shouldAdvanceFollowLive("running", true)).toBe(true);
    expect(shouldAdvanceFollowLive("running", false)).toBe(false);
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
    expect(marks[0].label).toMatch(/powerflow/i);
    expect(marks[0].label).not.toMatch(/tick\s*\d/i);
    expect(marks[1].label).toMatch(/not converged|failed/i);
  });

  it("emits one discrete marker per powerflow run (not a merged band)", () => {
    const marks = powerflowMarkersFromHistory([t0, t1, t2, t3, t4]);
    expect(marks.map((m) => m.index)).toEqual([0, 2, 3]);
    expect(new Set(marks.map((m) => m.index)).size).toBe(marks.length);
  });
});

describe("prevPowerflowIndex / nextPowerflowIndex", () => {
  const hist = [t0, t1, t2, t3, t4];

  it("jumps between samples where powerflow ran", () => {
    // t0 ran, t1 skipped, t2 ran (failed), t3 ran, t4 skipped
    expect(prevPowerflowIndex(hist, 4)).toBe(3);
    expect(prevPowerflowIndex(hist, 3)).toBe(2);
    expect(prevPowerflowIndex(hist, 2)).toBe(0);
    expect(prevPowerflowIndex(hist, 0)).toBe(null);
    expect(nextPowerflowIndex(hist, 0)).toBe(2);
    expect(nextPowerflowIndex(hist, 2)).toBe(3);
    expect(nextPowerflowIndex(hist, 3)).toBe(null);
  });

  it("returns null when no powerflow runs exist", () => {
    expect(prevPowerflowIndex([t1, t4], 1)).toBe(null);
    expect(nextPowerflowIndex([t1, t4], 0)).toBe(null);
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

  it("skips samples whose anomalies are not timeline-annotated", () => {
    const unknownOnly = {
      tick_index: 5,
      measurements: [{ timestamp: "2026-01-01T00:02:30Z", signal_id: "bus_1_vm_pu", value: 1 }],
      anomalies: [{ type: "mystery_detector", signal_id: "bus_1_vm_pu" }],
    };
    const hist2 = [t0, unknownOnly, t1];
    // orange markers only at t1 (index 2); unknown-only must not be a stop
    expect(anomalyMarkersFromHistory(hist2).map((m) => m.index)).toEqual([2]);
    expect(nextAnomalyIndex(hist2, 0)).toBe(2);
    expect(prevAnomalyIndex(hist2, 2)).toBe(null);
  });
});

describe("playheadFraction", () => {
  it("aligns the playhead with anomaly marker X on uneven time gaps", () => {
    const uneven = [
      {
        tick_index: 0,
        measurements: [{ timestamp: "2026-01-01T00:00:00Z", signal_id: "bus_1_vm_pu", value: 1 }],
        anomalies: [],
      },
      {
        tick_index: 1,
        measurements: [{ timestamp: "2026-01-01T00:00:10Z", signal_id: "bus_1_vm_pu", value: 1 }],
        anomalies: [{ type: "measurement_spike", signal_id: "bus_1_vm_pu" }],
      },
      {
        tick_index: 2,
        measurements: [{ timestamp: "2026-01-01T00:01:00Z", signal_id: "bus_1_vm_pu", value: 1 }],
        anomalies: [],
      },
    ];
    const marks = anomalyMarkersFromHistory(uneven);
    expect(marks).toHaveLength(1);
    // index fraction would be 0.5; time fraction is 10/60
    expect(playheadFraction(uneven, 1)).toBeCloseTo(10 / 60, 5);
    expect(playheadFraction(uneven, 1)).toBeCloseTo(
      markerFraction(
        { kind: "tick", index: 1, atMs: marks[0].atMs, label: "", ran: true },
        uneven,
      ),
      5,
    );
    expect(playheadFraction(uneven, 1)).not.toBeCloseTo(0.5, 2);
  });
});

describe("sortHistoryByTime", () => {
  it("orders samples so index 0 is the timeline start (left)", () => {
    const shuffled = [t2, t0, t1];
    const sorted = sortHistoryByTime(shuffled);
    expect(sorted.map((e) => e.tick_index)).toEqual([0, 1, 2]);
    expect(playheadFraction(sorted, 0)).toBe(0);
  });
});

describe("indexFromTimelineFraction", () => {
  it("maps a hover fraction to the nearest sample on the time axis", () => {
    const hist = [t0, t1, t2];
    expect(indexFromTimelineFraction(hist, 0)).toBe(0);
    expect(indexFromTimelineFraction(hist, 1)).toBe(2);
    expect(indexFromTimelineFraction(hist, 0.5)).toBe(1);
  });

  it("clamps out-of-range fractions and empty history", () => {
    expect(indexFromTimelineFraction([], 0.5)).toBe(0);
    expect(indexFromTimelineFraction([t0], 0.9)).toBe(0);
    expect(indexFromTimelineFraction([t0, t1, t2], -1)).toBe(0);
    expect(indexFromTimelineFraction([t0, t1, t2], 2)).toBe(2);
  });

  it("round-trips with playheadFraction for each sample", () => {
    const hist = [t0, t1, t2, t3, t4];
    for (let i = 0; i < hist.length; i += 1) {
      const f = playheadFraction(hist, i);
      expect(indexFromTimelineFraction(hist, f)).toBe(i);
    }
  });
});
