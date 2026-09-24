/**
 * Point-to-point directions -- source to destination, works for any
 * address in India (each request pulls only the OSM road network for
 * the area between the two points; see backend/app/services/
 * directions_service.py for how that's scoped). Distinct from the
 * multi-stop QPSO optimizer on the Optimization Studio page: for exactly
 * two points, "best route" is a plain shortest-path search, with up to
 * two alternates shown the way a consumer maps app would.
 */
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Navigation, ArrowRightLeft, Clock, Ruler } from "lucide-react";
import { directionsApi, type DirectionsResponse, type RouteOption } from "@/api/directions";
import { ApiError } from "@/api/client";
import { NetworkMap } from "@/components/map/NetworkMap";
import { EmptyState } from "@/components/common/EmptyState";

function formatDistance(m: number): string {
  return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m)} m`;
}

function formatDuration(s: number): string {
  const mins = Math.round(s / 60);
  if (mins < 60) return `${mins} min`;
  return `${Math.floor(mins / 60)} hr ${mins % 60} min`;
}

function bounds(routes: RouteOption[]): [[number, number], [number, number]] | undefined {
  const coords = routes.flatMap((r) => r.geometry);
  if (coords.length === 0) return undefined;
  const lons = coords.map((c) => c[0]);
  const lats = coords.map((c) => c[1]);
  return [
    [Math.min(...lons), Math.min(...lats)],
    [Math.max(...lons), Math.max(...lats)],
  ];
}

export function DirectionsPage() {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [criterion, setCriterion] = useState<"time" | "distance">("time");
  const [result, setResult] = useState<DirectionsResponse | null>(null);
  const [selectedRank, setSelectedRank] = useState(0);

  const mutation = useMutation({
    mutationFn: () =>
      directionsApi.get({
        origin: { address: origin.trim() },
        destination: { address: destination.trim() },
        criterion,
        alternates: true,
      }),
    onSuccess: (data) => {
      setResult(data);
      setSelectedRank(0);
    },
  });

  const canSubmit = origin.trim().length > 0 && destination.trim().length > 0 && !mutation.isPending;
  const selected = result?.routes.find((r) => r.rank === selectedRank);
  const others = result?.routes.filter((r) => r.rank !== selectedRank) ?? [];

  return (
    <div className="h-full flex flex-col">
      <div className="px-6 py-4 border-b border-base-800">
        <h1 className="text-lg font-semibold">Directions</h1>
        <p className="text-sm text-ink-500">Source to destination, anywhere in India.</p>
      </div>

      <div className="flex-1 flex min-h-0">
        <aside className="w-96 shrink-0 border-r border-base-800 p-4 overflow-y-auto space-y-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (canSubmit) mutation.mutate();
            }}
            className="space-y-3"
          >
            <div>
              <label className="label-caps block mb-1.5" htmlFor="origin">Source</label>
              <input
                id="origin"
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                placeholder="e.g. Connaught Place, New Delhi"
                className="input-field w-full"
                required
              />
            </div>

            <div className="flex justify-center">
              <button
                type="button"
                onClick={() => {
                  setOrigin(destination);
                  setDestination(origin);
                }}
                className="text-ink-500 hover:text-ink-100 p-1"
                aria-label="Swap source and destination"
                title="Swap"
              >
                <ArrowRightLeft size={14} />
              </button>
            </div>

            <div>
              <label className="label-caps block mb-1.5" htmlFor="destination">Destination</label>
              <input
                id="destination"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                placeholder="e.g. India Gate, New Delhi"
                className="input-field w-full"
                required
              />
            </div>

            <div className="flex items-center gap-1.5 pt-1">
              <button
                type="button"
                onClick={() => setCriterion("time")}
                className={`text-xs px-2.5 py-1 rounded-sm border transition-colors ${criterion === "time" ? "border-signal/40 bg-signal/10 text-signal" : "border-base-600 text-ink-500 hover:text-ink-100"}`}
              >
                Fastest
              </button>
              <button
                type="button"
                onClick={() => setCriterion("distance")}
                className={`text-xs px-2.5 py-1 rounded-sm border transition-colors ${criterion === "distance" ? "border-signal/40 bg-signal/10 text-signal" : "border-base-600 text-ink-500 hover:text-ink-100"}`}
              >
                Shortest
              </button>
            </div>

            {mutation.isError && (
              <p className="text-xs text-traffic-severe">
                {mutation.error instanceof ApiError ? mutation.error.message : "Could not find a route."}
              </p>
            )}

            <button type="submit" disabled={!canSubmit} className="btn-primary w-full flex items-center justify-center gap-1.5">
              <Navigation size={14} /> {mutation.isPending ? "Finding route…" : "Get Directions"}
            </button>
          </form>

          {result && (
            <div className="space-y-2 pt-2 border-t border-base-800">
              <p className="label-caps">{result.routes.length > 1 ? `${result.routes.length} routes found` : "Route"}</p>
              {result.routes.map((route) => (
                <button
                  key={route.rank}
                  onClick={() => setSelectedRank(route.rank)}
                  className={`w-full text-left rounded-md border px-3 py-2.5 transition-colors ${
                    route.rank === selectedRank
                      ? "border-signal/40 bg-signal/10"
                      : "border-base-700 hover:bg-base-900"
                  }`}
                >
                  <p className="text-sm font-medium">
                    {route.is_primary ? "Best route" : `Alternate ${route.rank}`}
                  </p>
                  <div className="flex items-center gap-3 mt-1 text-xs text-ink-500">
                    <span className="flex items-center gap-1"><Clock size={12} /> {formatDuration(route.duration_s)}</span>
                    <span className="flex items-center gap-1"><Ruler size={12} /> {formatDistance(route.distance_m)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </aside>

        <div className="flex-1 p-4 min-h-0">
          <div className="panel h-full p-2 relative">
            {!result && !mutation.isPending && (
              <EmptyState
                title="NO ROUTE YET"
                description="Enter a source and destination to see the path on the map."
                icon={<Navigation size={28} />}
              />
            )}
            {(result || mutation.isPending) && (
              <NetworkMap
                nodes={[]}
                edges={[]}
                selectedRoutePath={selected?.geometry}
                alternateRoutePaths={others.map((r) => r.geometry)}
                bounds={result ? bounds(result.routes) : undefined}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
