/**
 * Advanced per-vehicle route inspector (section 26). Clicking a stop
 * should highlight the corresponding map leg -- wire onStopSelect to the
 * map's selectedRouteNodeIds when this is mounted alongside NetworkMap.
 */
import type { RouteSummary } from "@/types/api";

export function RouteInspector({
  route,
  onStopSelect,
  active = false,
}: {
  route: RouteSummary;
  onStopSelect?: (seq: number) => void;
  active?: boolean;
}) {
  return (
    <div className={`panel p-4 transition-colors ${active ? "ring-1 ring-signal/50" : ""}`}>
      <div className="flex items-center justify-between mb-3">
        <p className="font-medium text-sm">Vehicle {route.vehicle_id?.slice(0, 8) ?? "—"}</p>
        <span className="text-xs text-ink-500">{route.stops.length} stops · {(route.distance_m / 1000).toFixed(1)} km</span>
      </div>
      <ol className="space-y-0">
        {route.stops.map((stop, i) => (
          <li key={stop.sequence_no}>
            <button
              onClick={() => onStopSelect?.(stop.sequence_no)}
              className="w-full text-left flex items-center gap-3 py-2 group"
            >
              <div className="flex flex-col items-center">
                <div className={`h-2 w-2 rounded-full ${stop.stop_type === "customer" ? "bg-signal" : "bg-ink-500"}`} />
                {i < route.stops.length - 1 && <div className="w-px h-6 bg-base-700" />}
              </div>
              <span className="text-sm text-ink-300 group-hover:text-ink-100 capitalize">
                {stop.stop_type === "customer" ? `Customer stop #${stop.sequence_no}` : stop.stop_type.replace("_", " ")}
              </span>
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
