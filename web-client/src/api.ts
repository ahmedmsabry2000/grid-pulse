export type FeatureCollection = {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    geometry: {
      type: string;
      coordinates: number[] | number[][];
    };
    properties: Record<string, unknown>;
  }>;
};

export type Topology = {
  network_id: string;
  seed: number;
  algorithm: string;
  buses: FeatureCollection;
  lines: FeatureCollection;
};

export type PowerflowResult = {
  ok: boolean;
  error: string | null;
  gate: Record<string, unknown> | null;
  powerflow: Record<string, unknown> | null;
  rating_exceedances: Array<Record<string, unknown>>;
  ensemble_anomalies: Array<Record<string, unknown>>;
  other_anomalies: Array<Record<string, unknown>>;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export function wsTelemetryUrl(): string {
  const configured = import.meta.env.VITE_WS_URL;
  if (configured) return configured;
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/ws/telemetry`;
}

export async function fetchNetworks(): Promise<string[]> {
  const r = await fetch(`${API_BASE}/networks`);
  if (!r.ok) throw new Error(`networks: ${r.status}`);
  const body = (await r.json()) as { networks: string[] };
  return body.networks;
}

export async function fetchTopology(networkId: string): Promise<Topology> {
  const r = await fetch(`${API_BASE}/networks/${encodeURIComponent(networkId)}/topology`);
  if (!r.ok) throw new Error(`topology: ${r.status}`);
  return (await r.json()) as Topology;
}

export async function postPowerflow(networkId: string): Promise<PowerflowResult> {
  const r = await fetch(`${API_BASE}/powerflow`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ network_id: networkId }),
  });
  if (!r.ok) throw new Error(`powerflow: ${r.status}`);
  return (await r.json()) as PowerflowResult;
}

export async function fetchEvents(limit = 500): Promise<unknown[]> {
  const r = await fetch(`${API_BASE}/events?limit=${encodeURIComponent(String(limit))}`);
  if (!r.ok) throw new Error(`events: ${r.status}`);
  const body = (await r.json()) as { events: unknown[] };
  return Array.isArray(body.events) ? body.events : [];
}

export type SimulatorStatus = {
  status: "running" | "stopped";
  pid: number | null;
};

async function readPlainError(r: Response, fallback: string): Promise<string> {
  try {
    const body = (await r.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) return body.detail;
  } catch {
    /* plain text only */
  }
  return `${fallback}: ${r.status}`;
}

export async function fetchSimulatorStatus(): Promise<SimulatorStatus> {
  const r = await fetch(`${API_BASE}/simulator`);
  if (!r.ok) throw new Error(await readPlainError(r, "simulator status"));
  const body = (await r.json()) as SimulatorStatus;
  return {
    status: body.status === "running" ? "running" : "stopped",
    pid: typeof body.pid === "number" ? body.pid : null,
  };
}

export async function postSimulatorStart(): Promise<SimulatorStatus> {
  const r = await fetch(`${API_BASE}/simulator/start`, { method: "POST" });
  if (!r.ok) throw new Error(await readPlainError(r, "simulator start"));
  const body = (await r.json()) as SimulatorStatus;
  return {
    status: body.status === "running" ? "running" : "stopped",
    pid: typeof body.pid === "number" ? body.pid : null,
  };
}

export async function postSimulatorStop(): Promise<SimulatorStatus> {
  const r = await fetch(`${API_BASE}/simulator/stop`, { method: "POST" });
  if (!r.ok) throw new Error(await readPlainError(r, "simulator stop"));
  const body = (await r.json()) as SimulatorStatus;
  return {
    status: body.status === "running" ? "running" : "stopped",
    pid: typeof body.pid === "number" ? body.pid : null,
  };
}

/** Fit OrthographicView to GeoJSON point extents with padding. */
export function boundsFromTopology(topo: Topology): [number, number, number, number] {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  const consider = (x: number, y: number) => {
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
  };
  for (const f of topo.buses.features) {
    if (f.geometry?.type === "Point" && Array.isArray(f.geometry.coordinates)) {
      const [x, y] = f.geometry.coordinates as number[];
      consider(x, y);
    }
  }
  if (!Number.isFinite(minX)) return [-1, -1, 1, 1];
  const pad = 0.15 * Math.max(maxX - minX, maxY - minY, 0.1);
  return [minX - pad, minY - pad, maxX + pad, maxY + pad];
}
