/**
 * Network Explorer (section 21). Immutable graph versions are never
 * editable in place -- only "import new version" / "activate" / "archive"
 * are exposed, matching the backend's immutability guarantee.
 */
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAppStore } from "@/store/useAppStore";
import { graphsApi } from "@/api/graphs";
import { projectsApi } from "@/api/projects";
import { depotsApi } from "@/api/depots";
import { customersApi } from "@/api/customers";
import { trafficApi } from "@/api/traffic";
import { NetworkMap } from "@/components/map/NetworkMap";
import { EmptyState } from "@/components/common/EmptyState";
import { NewDepotButton } from "@/components/forms/NewDepotModal";
import { Network as NetworkIcon } from "lucide-react";

export function NetworkPage() {
  const projectId = useAppStore((s) => s.currentProjectId);
  const trafficScenarioId = useAppStore((s) => s.currentTrafficScenarioId);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);

  const { data: versions, isLoading: versionsLoading } = useQuery({
    queryKey: ["graph-versions", projectId],
    queryFn: () => projectsApi.graphs(projectId!),
    enabled: !!projectId,
  });

  // Default to the newest version once versions load (list is already
  // ordered newest-first by the backend).
  useEffect(() => {
    if (!selectedVersionId && versions && versions.length > 0) {
      setSelectedVersionId(versions[0].id);
    }
  }, [versions, selectedVersionId]);

  const { data: topology, isLoading: topologyLoading } = useQuery({
    queryKey: ["graph-topology", selectedVersionId],
    queryFn: () => graphsApi.topology(selectedVersionId!),
    enabled: !!selectedVersionId,
  });

  const { data: depots } = useQuery({
    queryKey: ["depots", projectId],
    queryFn: () => depotsApi.list(projectId!),
    enabled: !!projectId,
  });

  const { data: customers } = useQuery({
    queryKey: ["customers", projectId, "map"],
    // The map wants every customer, not the API's default page of 50 --
    // the seed creates 60 (`num_customers` in dummy_data.py), and other
    // projects can have more. `list_customers` is a simple limit/cursor
    // cursor over `id > cursor`, now ordered by id (see the backend fix),
    // so a single generous limit is enough here without real pagination.
    queryFn: () => customersApi.list(projectId!, 2000),
    enabled: !!projectId,
  });

  // Per-edge congestion for the selected traffic scenario, so the map
  // colors roads by actual congestion instead of defaulting every edge to
  // 1 (green, thin) because NetworkMap never received congestionFactor.
  const { data: trafficEdges } = useQuery({
    queryKey: ["traffic-edges", trafficScenarioId],
    queryFn: () => trafficApi.edges(trafficScenarioId!),
    enabled: !!trafficScenarioId,
  });

  const congestionByEdge = useMemo(() => {
    const lookup = new Map<string, number>();
    trafficEdges?.forEach((e) => lookup.set(`${e.u}->${e.v}`, e.congestion_factor));
    return lookup;
  }, [trafficEdges]);

  // Bounding box of the current topology's nodes, memoized so its identity
  // only changes when the underlying node set actually changes -- passed
  // to NetworkMap as `bounds` so it can fitBounds once instead of
  // fighting the user's panning on every render (see NetworkMap).
  const bounds = useMemo<[[number, number], [number, number]] | undefined>(() => {
    const nodes = topology?.nodes;
    if (!nodes || nodes.length === 0) return undefined;
    let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity;
    for (const n of nodes) {
      if (n.lon < minLon) minLon = n.lon;
      if (n.lon > maxLon) maxLon = n.lon;
      if (n.lat < minLat) minLat = n.lat;
      if (n.lat > maxLat) maxLat = n.lat;
    }
    return [[minLon, minLat], [maxLon, maxLat]];
  }, [topology?.nodes]);

  if (!projectId) {
    return (
      <EmptyState
        title="NO PROJECT SELECTED"
        description="Choose a project from the context selector to explore its road network."
        icon={<NetworkIcon size={28} />}
      />
    );
  }

  return (
    <div className="h-full grid grid-cols-[320px_1fr]">
      <aside className="border-r border-base-800 p-4 overflow-y-auto">
        <h1 className="text-lg font-semibold mb-1">Network</h1>
        <p className="text-sm text-ink-500 mb-4">Graph versions for this project.</p>

        {versionsLoading && <p className="text-xs text-ink-500">Loading versions…</p>}

        {!versionsLoading && (!versions || versions.length === 0) && (
          <p className="text-xs text-ink-500">No graph versions yet. Import one to get started.</p>
        )}

        <div className="space-y-2">
          {versions?.map((v) => (
            <button
              key={v.id}
              onClick={() => setSelectedVersionId(v.id)}
              className={`panel-inset p-3 w-full text-left transition-colors ${
                v.id === selectedVersionId ? "ring-1 ring-signal/40" : ""
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-medium text-sm flex items-center gap-1.5">
                  <NetworkIcon size={13} /> Version {v.version_no}
                </span>
                <span className={`text-xs ${v.status === "ready" ? "text-traffic-normal" : "text-ink-700"}`}>{v.status}</span>
              </div>
              <p className="text-xs text-ink-500">{v.node_count} nodes · {v.edge_count} edges · {v.source}</p>
              {!v.is_connected && <p className="text-xs text-traffic-severe mt-1">Warning: graph is disconnected</p>}
            </button>
          ))}
        </div>
        <button className="btn-secondary w-full mt-4 text-xs">Import New Version</button>

        <div className="mt-6 pt-4 border-t border-base-800">
          <p className="label-caps mb-2">Depots ({depots?.length ?? 0})</p>
          <NewDepotButton projectId={projectId} />
        </div>
      </aside>
      <section className="p-4">
        <div className="panel h-full p-2 relative">
          {topologyLoading && (
            <div className="absolute inset-0 flex items-center justify-center text-sm text-ink-500 z-10">
              Loading network…
            </div>
          )}
          <NetworkMap
            nodes={topology?.nodes ?? []}
            edges={topology?.edges.map((e) => ({ u: e.u, v: e.v, congestionFactor: congestionByEdge.get(`${e.u}->${e.v}`) })) ?? []}
            depots={depots?.filter((d) => d.latitude != null && d.longitude != null)
              .map((d) => ({ id: d.id, lat: d.latitude!, lon: d.longitude!, name: d.name })) ?? []}
            customers={customers?.filter((c) => c.latitude != null && c.longitude != null)
              .map((c) => ({ id: c.id, lat: c.latitude!, lon: c.longitude! })) ?? []}
            bounds={bounds}
          />
        </div>
      </section>
    </div>
  );
}
