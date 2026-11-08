import { afterEach, describe, expect, it, vi } from "vitest";
import {
  Topology,
  boundsFromTopology,
  fetchSimulatorStatus,
  postSimulatorStart,
  postSimulatorStop,
} from "./api";

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

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("boundsFromTopology", () => {
  it("pads extents", () => {
    const [minX, minY, maxX, maxY] = boundsFromTopology(sample);
    expect(minX).toBeLessThan(0);
    expect(minY).toBeLessThan(0);
    expect(maxX).toBeGreaterThan(2);
    expect(maxY).toBeGreaterThan(1);
  });
});

describe("simulator toggle API", () => {
  it("GETs /simulator for status", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "stopped", pid: null }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const st = await fetchSimulatorStatus();
    expect(st.status).toBe("stopped");
    expect(fetchMock).toHaveBeenCalledWith("/api/simulator");
  });

  it("POSTs /simulator/start and /simulator/stop", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "running", pid: 4242 }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "stopped", pid: null }),
      });
    vi.stubGlobal("fetch", fetchMock);
    const started = await postSimulatorStart();
    expect(started).toEqual({ status: "running", pid: 4242 });
    expect(fetchMock.mock.calls[0][0]).toBe("/api/simulator/start");
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: "POST" });

    const stopped = await postSimulatorStop();
    expect(stopped.status).toBe("stopped");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/simulator/stop");
  });

  it("surfaces plain-text start errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ detail: "failed to start simulator: missing binary" }),
      }),
    );
    await expect(postSimulatorStart()).rejects.toThrow(/missing binary/);
  });
});
