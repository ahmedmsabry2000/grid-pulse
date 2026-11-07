import { describe, expect, it } from "vitest";
import { Topology, boundsFromTopology } from "./api";

const sample: Topology = {
  network_id: "case14",
  seed: 42,
  algorithm: "spring",
  buses: {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: { type: "Point", coordinates: [0, 0] },
        properties: { bus_id: 0 },
      },
      {
        type: "Feature",
        geometry: { type: "Point", coordinates: [2, 1] },
        properties: { bus_id: 1 },
      },
    ],
  },
  lines: { type: "FeatureCollection", features: [] },
};

describe("boundsFromTopology", () => {
  it("pads extents", () => {
    const [minX, minY, maxX, maxY] = boundsFromTopology(sample);
    expect(minX).toBeLessThan(0);
    expect(minY).toBeLessThan(0);
    expect(maxX).toBeGreaterThan(2);
    expect(maxY).toBeGreaterThan(1);
  });
});
