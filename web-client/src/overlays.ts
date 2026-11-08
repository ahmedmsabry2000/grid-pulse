/** Map Stage 6 anomaly events onto topology bus/line ids for deck.gl layers. */

export type AnomalyEvent = {
  type: string;
  signal_id: string;
  score?: number | string;
  detail?: string;
  quantity?: string;
};

export type OverlayKind = "measurement" | "pf_output" | "rating";

export type OverlayHit = {
  kind: OverlayKind;
  busId?: number;
  lineId?: number;
  trafoId?: number;
  signalId: string;
  type: string;
};

const MEASUREMENT_TYPES = new Set([
  "measurement_spike",
  "measurement_zscore",
  "measurement_ensemble",
]);

const PF_TYPES = new Set(["pf_residual"]);

const RATING_TYPES = new Set(["rating_exceedance"]);

export function classifyAnomaly(type: string): OverlayKind | null {
  if (MEASUREMENT_TYPES.has(type)) return "measurement";
  if (PF_TYPES.has(type)) return "pf_output";
  if (RATING_TYPES.has(type)) return "rating";
  return null;
}

/** bus_N_* signals use 1-based labels; topology bus_id is 0-based pandapower index. */
export function busIdFromSignal(signalId: string): number | undefined {
  const m = /^bus_(\d+)(?:_|$)/.exec(signalId);
  if (!m) return undefined;
  const label = Number(m[1]);
  if (!Number.isFinite(label) || label < 1) return undefined;
  return label - 1;
}

export function elementIdsFromSignal(signalId: string): {
  lineId?: number;
  trafoId?: number;
} {
  const line = /^line:(\d+)$/.exec(signalId);
  if (line) return { lineId: Number(line[1]) };
  const trafo = /^trafo:(\d+)$/.exec(signalId);
  if (trafo) return { trafoId: Number(trafo[1]) };
  return {};
}

export function anomaliesToOverlayHits(anomalies: AnomalyEvent[]): OverlayHit[] {
  const hits: OverlayHit[] = [];
  for (const a of anomalies) {
    const kind = classifyAnomaly(a.type);
    if (!kind) continue;
    const busId = busIdFromSignal(a.signal_id);
    const { lineId, trafoId } = elementIdsFromSignal(a.signal_id);
    hits.push({
      kind,
      busId,
      lineId,
      trafoId,
      signalId: a.signal_id,
      type: a.type,
    });
  }
  return hits;
}

export type OrthoViewState = {
  target: [number, number, number];
  zoom: number;
  minZoom: number;
  maxZoom: number;
};

export type ViewportSize = {
  width: number;
  height: number;
};

/**
 * OrthographicView target/zoom that fits [minX,minY,maxX,maxY] into a viewport.
 *
 * deck.gl OrthographicView: zoom 0 maps 1 world unit → 1 pixel. Fitting must use
 * the viewport size in pixels; a unitless "span target" collapses the graph to a
 * couple of pixels and looks like a blank map.
 */
export function viewStateFromBounds(
  bounds: readonly [number, number, number, number],
  viewport: ViewportSize = { width: 800, height: 600 },
  fill = 0.85,
): OrthoViewState {
  const [minX, minY, maxX, maxY] = bounds;
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  const spanX = Math.max(maxX - minX, 1e-6);
  const spanY = Math.max(maxY - minY, 1e-6);
  const width = Math.max(viewport.width, 1);
  const height = Math.max(viewport.height, 1);
  const zoom = Math.min(
    Math.log2((width * fill) / spanX),
    Math.log2((height * fill) / spanY),
  );
  return {
    target: [cx, cy, 0],
    zoom,
    minZoom: -4,
    maxZoom: 16,
  };
}
