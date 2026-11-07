import { OrthographicView } from "@deck.gl/core";
import { GeoJsonLayer, ScatterplotLayer } from "@deck.gl/layers";
import DeckGL from "@deck.gl/react";
import { useMemo } from "react";
import { Topology, boundsFromTopology } from "./api";

type Props = {
  topology: Topology | null;
};

export default function NetworkMap({ topology }: Props) {
  const bounds = useMemo(
    () => (topology ? boundsFromTopology(topology) : ([-1, -1, 1, 1] as const)),
    [topology],
  );
  const [minX, minY, maxX, maxY] = bounds;
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  const zoom = Math.log2(1.6 / Math.max(maxX - minX, maxY - minY, 0.2));

  const layers = useMemo(() => {
    if (!topology) return [];
    return [
      new GeoJsonLayer({
        id: "lines",
        // Orthographic synthetic coords; cast avoids deck.gl GeoJSON generics friction
        data: topology.lines as never,
        stroked: true,
        filled: false,
        getLineColor: [74, 126, 181, 220],
        getLineWidth: 2,
        lineWidthUnits: "pixels",
        pickable: true,
      }),
      new ScatterplotLayer({
        id: "buses",
        data: topology.buses.features,
        getPosition: (d: { geometry: { coordinates: number[] } }) =>
          d.geometry.coordinates as [number, number],
        getFillColor: [226, 176, 74, 240],
        getRadius: 6,
        radiusUnits: "pixels",
        pickable: true,
      }),
    ];
  }, [topology]);

  return (
    <DeckGL
      views={new OrthographicView({ id: "ortho", flipY: false })}
      initialViewState={{
        target: [cx, cy, 0],
        zoom,
        minZoom: -4,
        maxZoom: 8,
      }}
      controller={true}
      layers={layers}
      getTooltip={({ object }) => {
        if (!object) return null;
        const props = object.properties ?? object;
        if (props?.bus_id != null) return `bus ${props.bus_id}`;
        if (props?.line_id != null) return `line ${props.line_id}`;
        if (props?.trafo_id != null) return `trafo ${props.trafo_id}`;
        return null;
      }}
    />
  );
}
