import { OrthographicView } from "@deck.gl/core";
import { GeoJsonLayer, ScatterplotLayer } from "@deck.gl/layers";
import DeckGL from "@deck.gl/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Topology, boundsFromTopology } from "./api";
import { OverlayHit, OverlayKind, viewStateFromBounds } from "./overlays";

type Props = {
  topology: Topology | null;
  overlays?: OverlayHit[];
};

const KIND_BUS_COLOR: Record<OverlayKind, [number, number, number, number]> = {
  measurement: [226, 120, 48, 255],
  pf_output: [46, 160, 160, 255],
  rating: [196, 72, 72, 255],
};

const KIND_LINE_COLOR: Record<OverlayKind, [number, number, number, number]> = {
  measurement: [226, 120, 48, 230],
  pf_output: [46, 160, 160, 230],
  rating: [196, 72, 72, 240],
};

function pickKind(
  kinds: OverlayKind[],
): OverlayKind | null {
  if (kinds.includes("rating")) return "rating";
  if (kinds.includes("pf_output")) return "pf_output";
  if (kinds.includes("measurement")) return "measurement";
  return null;
}

export default function NetworkMap({ topology, overlays = [] }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [viewport, setViewport] = useState({ width: 800, height: 600 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) {
        setViewport({ width, height });
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const bounds = useMemo(
    () => (topology ? boundsFromTopology(topology) : ([-1, -1, 1, 1] as const)),
    [topology],
  );

  const [viewState, setViewState] = useState(() =>
    viewStateFromBounds(bounds, viewport),
  );

  useEffect(() => {
    setViewState(viewStateFromBounds(bounds, viewport));
  }, [bounds, viewport, topology?.network_id]);

  const busKinds = useMemo(() => {
    const map = new Map<number, OverlayKind[]>();
    for (const h of overlays) {
      if (h.busId == null) continue;
      const list = map.get(h.busId) ?? [];
      list.push(h.kind);
      map.set(h.busId, list);
    }
    return map;
  }, [overlays]);

  const lineKinds = useMemo(() => {
    const map = new Map<string, OverlayKind[]>();
    for (const h of overlays) {
      if (h.lineId != null) {
        const key = `line:${h.lineId}`;
        const list = map.get(key) ?? [];
        list.push(h.kind);
        map.set(key, list);
      }
      if (h.trafoId != null) {
        const key = `trafo:${h.trafoId}`;
        const list = map.get(key) ?? [];
        list.push(h.kind);
        map.set(key, list);
      }
    }
    return map;
  }, [overlays]);

  const layers = useMemo(() => {
    if (!topology) return [];
    return [
      new GeoJsonLayer({
        id: "lines",
        data: topology.lines as never,
        stroked: true,
        filled: false,
        getLineColor: (f: {
          properties?: { line_id?: number; trafo_id?: number; kind?: string };
        }) => {
          const props = f.properties ?? {};
          const key =
            props.line_id != null
              ? `line:${props.line_id}`
              : props.trafo_id != null
                ? `trafo:${props.trafo_id}`
                : "";
          const kind = pickKind(lineKinds.get(key) ?? []);
          if (kind) return KIND_LINE_COLOR[kind];
          return [74, 126, 181, 220];
        },
        getLineWidth: (f: {
          properties?: { line_id?: number; trafo_id?: number };
        }) => {
          const props = f.properties ?? {};
          const key =
            props.line_id != null
              ? `line:${props.line_id}`
              : props.trafo_id != null
                ? `trafo:${props.trafo_id}`
                : "";
          return lineKinds.has(key) ? 5 : 2;
        },
        lineWidthUnits: "pixels",
        updateTriggers: {
          getLineColor: [lineKinds],
          getLineWidth: [lineKinds],
        },
        pickable: true,
      }),
      new ScatterplotLayer({
        id: "buses",
        data: topology.buses.features,
        getPosition: (d: { geometry: { coordinates: number[] } }) =>
          d.geometry.coordinates as [number, number],
        getFillColor: (d: { properties?: { bus_id?: number } }) => {
          const id = d.properties?.bus_id;
          const kind = id != null ? pickKind(busKinds.get(id) ?? []) : null;
          if (kind) return KIND_BUS_COLOR[kind];
          return [226, 176, 74, 240];
        },
        getRadius: (d: { properties?: { bus_id?: number } }) => {
          const id = d.properties?.bus_id;
          return id != null && busKinds.has(id) ? 10 : 6;
        },
        radiusUnits: "pixels",
        updateTriggers: {
          getFillColor: [busKinds],
          getRadius: [busKinds],
        },
        pickable: true,
      }),
    ];
  }, [topology, busKinds, lineKinds]);

  return (
    <div ref={containerRef} className="network-map">
      <DeckGL
        views={new OrthographicView({ id: "ortho", flipY: false })}
        viewState={viewState}
        onViewStateChange={({ viewState: next }) =>
          setViewState(next as typeof viewState)
        }
        controller={true}
        layers={layers}
        getTooltip={({ object }) => {
          if (!object) return null;
          const props = object.properties ?? object;
          if (props?.bus_id != null) {
            const kinds = busKinds.get(Number(props.bus_id)) ?? [];
            const suffix = kinds.length ? ` · ${kinds.join(",")}` : "";
            return `bus ${props.bus_id}${suffix}`;
          }
          if (props?.line_id != null) {
            const kinds = lineKinds.get(`line:${props.line_id}`) ?? [];
            const suffix = kinds.length ? ` · ${kinds.join(",")}` : "";
            return `line ${props.line_id}${suffix}`;
          }
          if (props?.trafo_id != null) {
            const kinds = lineKinds.get(`trafo:${props.trafo_id}`) ?? [];
            const suffix = kinds.length ? ` · ${kinds.join(",")}` : "";
            return `trafo ${props.trafo_id}${suffix}`;
          }
          return null;
        }}
      />
    </div>
  );
}
