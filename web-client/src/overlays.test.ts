import { describe, expect, it } from "vitest";
import {
  anomaliesToOverlayHits,
  busIdFromSignal,
  classifyAnomaly,
  elementIdsFromSignal,
  viewStateFromBounds,
} from "./overlays";

describe("classifyAnomaly", () => {
  it("splits measurement / pf / rating", () => {
    expect(classifyAnomaly("measurement_spike")).toBe("measurement");
    expect(classifyAnomaly("measurement_ensemble")).toBe("measurement");
    expect(classifyAnomaly("pf_residual")).toBe("pf_output");
    expect(classifyAnomaly("rating_exceedance")).toBe("rating");
    expect(classifyAnomaly("unknown")).toBeNull();
  });
});

describe("busIdFromSignal", () => {
  it("maps 1-based bus labels to 0-based topology ids", () => {
    expect(busIdFromSignal("bus_1_vm_pu")).toBe(0);
    expect(busIdFromSignal("bus_14_vm_pu")).toBe(13);
    expect(busIdFromSignal("load_0_p_mw")).toBeUndefined();
  });
});

describe("elementIdsFromSignal", () => {
  it("parses rating signal ids", () => {
    expect(elementIdsFromSignal("line:3")).toEqual({ lineId: 3 });
    expect(elementIdsFromSignal("trafo:0")).toEqual({ trafoId: 0 });
  });
});

describe("anomaliesToOverlayHits", () => {
  it("builds hits for mixed anomaly types", () => {
    const hits = anomaliesToOverlayHits([
      { type: "measurement_spike", signal_id: "bus_2_vm_pu" },
      { type: "rating_exceedance", signal_id: "line:4" },
      { type: "pf_residual", signal_id: "bus_3_vm_pu" },
    ]);
    expect(hits).toHaveLength(3);
    expect(hits[0]).toMatchObject({ kind: "measurement", busId: 1 });
    expect(hits[1]).toMatchObject({ kind: "rating", lineId: 4 });
    expect(hits[2]).toMatchObject({ kind: "pf_output", busId: 2 });
  });
});

describe("viewStateFromBounds", () => {
  it("centers and zooms to span", () => {
    const vs = viewStateFromBounds([-1, -2, 3, 4]);
    expect(vs.target[0]).toBe(1);
    expect(vs.target[1]).toBe(1);
    expect(vs.zoom).toBeGreaterThan(-5);
  });
});
