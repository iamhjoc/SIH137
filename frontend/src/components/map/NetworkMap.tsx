/**
 * MapLibre GL wrapper -- the command-center map. Renders road network,
 * traffic-state coloring, depots/customers, and selected/candidate routes
 * with a distinctive visual language (not a generic basemap clone):
 *   - normal road:      thin muted line
 *   - congested road:   traffic-state colored, weight scales with severity
 *   - selected route:   animated directional dash flow
 *   - candidate route:  subtle dashed animated path
 *
 * Loaded dynamically (see OptimizationPage/OperationsPage) so MapLibre's
 * bundle only ships to routes that actually render a map.
 *
 * The map instance itself is created once on mount; everything it draws
 * (roads/depots/customers/selected route) is kept in sync on every
 * subsequent prop change via `syncMapData`, since props routinely arrive
 * after mount here (async data fetched through TanStack Query).
 */
import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import type { GeoJSONSource, Map as MLMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useAppStore, type MapLayerKey } from "@/store/useAppStore";

interface GeoNode { id: string; lat: number; lon: number }
interface GeoEdge { u: string; v: string; congestionFactor?: number }

interface Props {
  nodes: GeoNode[];
  edges: GeoEdge[];
  depots?: { id: string; lat: number; lon: number; name: string }[];
  customers?: { id: string; lat: number; lon: number }[];
  /** Highlight a route by its graph node ids (resolved against `nodes`). */
  selectedRouteNodeIds?: string[];
  /** Highlight a route by raw [lon, lat] coordinates -- takes priority over
   * selectedRouteNodeIds when both are given, and doesn't require the full
   * node list to be loaded (e.g. when drawing a job's persisted geometry). */
  selectedRoutePath?: [number, number][];
  /** Other candidate routes to draw dimmed/thin alongside the selected one
   * (e.g. Directions alternates) -- purely presentational, not clickable. */
  alternateRoutePaths?: [number, number][][];
  /** Initial camera center, used only when the map is first created (before
   * `bounds` below has a chance to fit it properly). */
  center?: [number, number];
  /** [[minLon,minLat],[maxLon,maxLat]] of the data to display. Fit once per
   * distinct value (see the effect below) rather than every render, so
   * panning isn't fought by a competing setCenter/fitBounds on each
   * unrelated prop change. */
  bounds?: [[number, number], [number, number]];
}

/**
 * Basemap tiles: by default this uses free, no-key OSM raster tiles at
 * demo-appropriate volume. For public production traffic, set
 * VITE_MAP_TILE_URL (and VITE_MAP_TILE_KEY if your provider needs one --
 * e.g. MapTiler, Stadia Maps, Mapbox, or Mappls' own tile service) in your
 * deployment env vars; nothing else in this file needs to change.
 * OSM's tile usage policy (https://operations.osmfoundation.org/policies/tiles/)
 * does not permit heavy production traffic on the free tile server -- swap
 * in a paid tile provider before real public usage.
 */
function buildBaseStyle(): maplibregl.StyleSpecification {
  const tileUrl = import.meta.env.VITE_MAP_TILE_URL;
  const tileKey = import.meta.env.VITE_MAP_TILE_KEY;

  if (tileUrl) {
    const url = tileKey ? `${tileUrl}${tileUrl.includes("?") ? "&" : "?"}key=${tileKey}` : tileUrl;
    return {
      version: 8,
      sources: { basemap: { type: "raster", tiles: [url], tileSize: 256 } },
      layers: [
        { id: "bg", type: "background", paint: { "background-color": "#0d0f12" } },
        { id: "basemap", type: "raster", source: "basemap", paint: { "raster-opacity": 0.55, "raster-brightness-min": 0, "raster-brightness-max": 0.5 } },
      ],
    };
  }

  return {
    version: 8,
    sources: { basemap: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, attribution: "\u00a9 OpenStreetMap contributors" } },
    layers: [
      { id: "bg", type: "background", paint: { "background-color": "#0d0f12" } },
      { id: "basemap", type: "raster", source: "basemap", paint: { "raster-opacity": 0.5, "raster-brightness-min": 0, "raster-brightness-max": 0.45 } },
    ],
  };
}

const DARK_STYLE: maplibregl.StyleSpecification = buildBaseStyle();

export function NetworkMap({ nodes, edges, depots = [], customers = [], selectedRouteNodeIds = [], selectedRoutePath, alternateRoutePaths = [], center, bounds }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const styleLoadedRef = useRef(false);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const syncMapDataRef = useRef<() => void>(() => {});
  const layers = useAppStore((s) => s.mapLayers);

  // Create the map instance exactly once.
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const fallbackCenter: [number, number] = [75.86, 30.9];

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: DARK_STYLE,
      center: center ?? fallbackCenter,
      zoom: 13,
      attributionControl: false,
    });
    mapRef.current = map;

    map.on("load", () => {
      styleLoadedRef.current = true;
      // Call through the ref, not the closure captured when this effect
      // ran (which only ever saw the initial, often-empty props) -- see
      // the effect below that keeps the ref pointed at the latest
      // syncMapData on every render.
      syncMapDataRef.current();
    });

    return () => {
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];
      map.remove();
      mapRef.current = null;
      styleLoadedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function syncMapData() {
    const map = mapRef.current;
    if (!map || !styleLoadedRef.current) return;
    const nodeLookup = new Map(nodes.map((n) => [n.id, n]));

    // Roads
    const roadFeatures = edges
      .map((e) => {
        const u = nodeLookup.get(e.u);
        const v = nodeLookup.get(e.v);
        if (!u || !v) return null;
        return {
          type: "Feature" as const,
          properties: { congestion: e.congestionFactor ?? 1 },
          geometry: { type: "LineString" as const, coordinates: [[u.lon, u.lat], [v.lon, v.lat]] },
        };
      })
      .filter((f): f is NonNullable<typeof f> => f !== null);
    const roadData = { type: "FeatureCollection" as const, features: roadFeatures };

    const roadsSource = map.getSource("roads") as GeoJSONSource | undefined;
    const congestionColor: any = ["interpolate", ["linear"], ["get", "congestion"],
      0.2, "#b3245c", 0.45, "#d84f4f", 0.65, "#e07a3f", 0.85, "#d9a441", 1, "#3fb27f"];
    const congestionWidth: any = ["interpolate", ["linear"], ["get", "congestion"], 0.2, 5, 1, 2];

    if (roadsSource) {
      roadsSource.setData(roadData);
    } else {
      map.addSource("roads", { type: "geojson", data: roadData });
      map.addLayer({
        id: "roads-line",
        type: "line",
        source: "roads",
        layout: { "line-cap": "round" },
        paint: { "line-color": congestionColor, "line-width": congestionWidth, "line-opacity": 0.9 },
      });
    }
    // "roads" toggle: layer visibility. "traffic" toggle: congestion
    // coloring/weighting vs a flat neutral line -- both are no-ops without
    // this, since the layer above is only ever created once.
    if (map.getLayer("roads-line")) {
      map.setLayoutProperty("roads-line", "visibility", layers.roads ? "visible" : "none");
      map.setPaintProperty("roads-line", "line-color", layers.traffic ? congestionColor : "#5b6472");
      map.setPaintProperty("roads-line", "line-width", layers.traffic ? congestionWidth : 2);
    }

    // Selected route -- prefer an explicit coordinate path (e.g. a job's
    // persisted geometry) over resolving node ids against `nodes`.
    const routeCoords: number[][] = selectedRoutePath?.length
      ? selectedRoutePath
      : selectedRouteNodeIds
          .map((id) => nodeLookup.get(id))
          .filter((n): n is GeoNode => !!n)
          .map((n) => [n.lon, n.lat]);

    const routeSource = map.getSource("selected-route") as GeoJSONSource | undefined;
    const routeData = { type: "Feature" as const, properties: {}, geometry: { type: "LineString" as const, coordinates: routeCoords } };
    if (routeCoords.length > 1 && layers.routes) {
      if (routeSource) {
        routeSource.setData(routeData);
      } else {
        map.addSource("selected-route", { type: "geojson", data: routeData });
        map.addLayer({
          id: "selected-route-line",
          type: "line",
          source: "selected-route",
          paint: { "line-color": "#5eead4", "line-width": 4, "line-dasharray": [0, 2, 3] },
        });
      }
    } else if (routeSource) {
      routeSource.setData({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [] } });
    }

    // Alternate routes -- dimmed, thin, non-interactive; drawn once as a
    // FeatureCollection so re-syncs just replace the whole source's data.
    const alternateData = {
      type: "FeatureCollection" as const,
      features: alternateRoutePaths
        .filter((coords) => coords.length > 1)
        .map((coords) => ({
          type: "Feature" as const,
          properties: {},
          geometry: { type: "LineString" as const, coordinates: coords },
        })),
    };
    const alternateSource = map.getSource("alternate-routes") as GeoJSONSource | undefined;
    if (alternateSource) {
      alternateSource.setData(alternateData);
    } else if (alternateData.features.length > 0) {
      map.addSource("alternate-routes", { type: "geojson", data: alternateData });
      // Insert below the selected-route layer so the chosen route always
      // draws on top of, not under, its alternates.
      map.addLayer(
        {
          id: "alternate-routes-line",
          type: "line",
          source: "alternate-routes",
          layout: { "line-cap": "round" },
          paint: { "line-color": "#8a919e", "line-width": 3, "line-opacity": 0.55 },
        },
        map.getLayer("selected-route-line") ? "selected-route-line" : undefined,
      );
    }

    // Depots -- markers, not a GeoJSON source, so just rebuild them.
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = layers.depots
      ? depots.map((d) =>
          new maplibregl.Marker({ color: "#5eead4" }).setLngLat([d.lon, d.lat]).setPopup(new maplibregl.Popup().setText(d.name)).addTo(map),
        )
      : [];

    // Customers
    const customerFeatures = customers.map((c) => ({
      type: "Feature" as const, properties: {}, geometry: { type: "Point" as const, coordinates: [c.lon, c.lat] },
    }));
    const customerData = { type: "FeatureCollection" as const, features: customerFeatures };
    const customersSource = map.getSource("customers") as GeoJSONSource | undefined;

    if (layers.customers) {
      if (customersSource) {
        customersSource.setData(customerData);
      } else {
        map.addSource("customers", { type: "geojson", data: customerData, cluster: true, clusterRadius: 40 });
        map.addLayer({
          id: "customer-clusters", type: "circle", source: "customers", filter: ["has", "point_count"],
          paint: { "circle-color": "#22262d", "circle-stroke-color": "#5eead4", "circle-stroke-width": 1, "circle-radius": ["step", ["get", "point_count"], 12, 25, 16, 100, 20] },
        });
        map.addLayer({
          id: "customer-points", type: "circle", source: "customers", filter: ["!", ["has", "point_count"]],
          paint: { "circle-color": "#8a919e", "circle-radius": 3 },
        });
      }
    } else if (customersSource) {
      customersSource.setData({ type: "FeatureCollection", features: [] });
    }
  }

  // Keep the ref pointed at the latest syncMapData closure on every
  // render, so the one-time "load" handler above always calls a version
  // with up-to-date props instead of the stale, first-render one.
  syncMapDataRef.current = syncMapData;

  // Re-sync whenever any of the drawable data changes -- including the
  // very common case of it arriving asynchronously after mount, and
  // whenever a layer visibility toggle (roads/traffic/routes/customers/
  // depots) flips.
  useEffect(() => {
    syncMapData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges, depots, customers, selectedRouteNodeIds, selectedRoutePath, alternateRoutePaths, layers.roads, layers.traffic, layers.routes, layers.customers, layers.depots]);

  // Fit the camera to the data's bounds once per distinct bounds value
  // (the caller is expected to memoize `bounds` so its identity is stable
  // across renders that don't actually change the underlying node set --
  // see NetworkPage). This replaces naively calling setCenter on every
  // render with nodes[0], which put the camera on the grid's corner and
  // fought the user's own panning.
  const boundsKeyRef = useRef<string | null>(null);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !bounds) return;
    const key = JSON.stringify(bounds);
    if (boundsKeyRef.current === key) return;
    boundsKeyRef.current = key;

    const fit = () => map.fitBounds(bounds, { padding: 48, duration: 0 });
    if (styleLoadedRef.current) {
      fit();
    } else {
      map.once("load", fit);
    }
  }, [bounds]);

  return <div ref={containerRef} className="h-full w-full rounded-lg overflow-hidden" role="application" aria-label="Road network map" />;
}

export function MapLayerToggle({ layerKey, label }: { layerKey: MapLayerKey; label: string }) {
  const enabled = useAppStore((s) => s.mapLayers[layerKey]);
  const toggle = useAppStore((s) => s.toggleMapLayer);
  return (
    <button
      onClick={() => toggle(layerKey)}
      aria-pressed={enabled}
      className={`text-xs px-2.5 py-1 rounded-sm border transition-colors ${
        enabled ? "border-signal/40 bg-signal/10 text-signal" : "border-base-600 text-ink-500 hover:text-ink-100"
      }`}
    >
      {label}
    </button>
  );
}
