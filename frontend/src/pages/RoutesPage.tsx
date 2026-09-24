import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { optimizationApi } from "@/api/optimization";
import { graphsApi } from "@/api/graphs";
import { useAppStore } from "@/store/useAppStore";
import { ResultsSummary } from "@/components/results/ResultsSummary";
import { RouteInspector } from "@/components/results/RouteInspector";
import { NetworkMap } from "@/components/map/NetworkMap";
import { EmptyState } from "@/components/common/EmptyState";
import { Route } from "lucide-react";

function routeKey(route: { vehicle_id: string | null; sequence_no: number }): string {
  return route.vehicle_id ?? `seq-${route.sequence_no}`;
}

export function RoutesPage() {
  // jobId can arrive two ways: as a URL param (/routes/:jobId, e.g. from the
  // History page or a shared link) or as the id of the job most recently
  // launched from the Optimization Studio (stored in useAppStore). URL wins
  // when present so a direct link always shows that specific job's routes.
  const { jobId: jobIdParam } = useParams<{ jobId: string }>();
  const lastJobId = useAppStore((s) => s.lastOptimizationJobId);
  const jobId = jobIdParam ?? lastJobId ?? undefined;

  const selectedKey = useAppStore((s) => s.selectedRouteVehicleId);
  const setSelectedRoute = useAppStore((s) => s.setSelectedRoute);

  const { data: result, isLoading } = useQuery({
    queryKey: ["optimization-routes", jobId],
    queryFn: () => optimizationApi.routes(jobId!),
    enabled: !!jobId,
  });

  const graphVersionId = result?.provenance.graph_version;
  const { data: topology } = useQuery({
    queryKey: ["graph-topology", graphVersionId],
    queryFn: () => graphsApi.topology(graphVersionId!),
    enabled: !!graphVersionId,
  });

  if (!jobId) {
    return (
      <EmptyState
        title="NO OPTIMIZATION RUNS"
        description="Your project has not been optimized yet. Create your first optimization run to generate traffic-aware fleet routes."
        icon={<Route size={28} />}
        action={{ label: "Start Optimization", onClick: () => (window.location.href = "/optimization") }}
      />
    );
  }

  if (isLoading || !result) {
    return <div className="p-6 text-sm text-ink-500">Loading route results…</div>;
  }

  const selectedRoute = result.routes.find((r) => routeKey(r) === selectedKey) ?? result.routes[0];

  return (
    <div className="h-full grid grid-cols-[1fr_360px]">
      <div className="p-4 overflow-y-auto space-y-4">
        <ResultsSummary result={result} />
        <div className="panel h-[420px] p-2">
          <NetworkMap
            nodes={topology?.nodes ?? []}
            edges={topology?.edges.map((e) => ({ u: e.u, v: e.v })) ?? []}
            selectedRoutePath={selectedRoute?.path}
          />
        </div>
      </div>
      <aside className="border-l border-base-800 p-4 overflow-y-auto space-y-3">
        <p className="label-caps">Vehicle Routes</p>
        {result.routes.map((r) => (
          <button key={routeKey(r)} onClick={() => setSelectedRoute(routeKey(r))} className="w-full text-left">
            <RouteInspector route={r} active={routeKey(r) === (selectedKey ?? routeKey(result.routes[0]))} />
          </button>
        ))}
      </aside>
    </div>
  );
}
