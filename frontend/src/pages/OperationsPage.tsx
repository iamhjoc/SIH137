/**
 * Operations Dashboard -- the primary command center KPI + map layer.
 * Every KPI is either a direct real count (vehicles/customers/job count)
 * or derived from the most recent SUCCEEDED optimization job's real
 * results. Where there's no completed run yet to derive a metric from,
 * the card is replaced with a plain status message rather than a
 * plausible-looking fake number.
 */
import { useQuery } from "@tanstack/react-query";
import { Truck, Users, Gauge, Clock, Flame, Activity, CheckCircle2 } from "lucide-react";
import { KpiCard } from "@/components/kpi/KpiCard";
import { KpiCardSkeleton } from "@/components/common/Skeletons";
import { NetworkMap, MapLayerToggle } from "@/components/map/NetworkMap";
import { useAppStore } from "@/store/useAppStore";
import { vehiclesApi } from "@/api/vehicles";
import { customersApi } from "@/api/customers";
import { depotsApi } from "@/api/depots";
import { optimizationApi } from "@/api/optimization";
import { graphsApi } from "@/api/graphs";

function StatusCard({ label, text }: { label: string; text: string }) {
  return (
    <div className="panel p-4 flex flex-col justify-center gap-1">
      <span className="label-caps">{label}</span>
      <span className="text-sm text-ink-500">{text}</span>
    </div>
  );
}

export function OperationsPage() {
  const { currentProjectId, currentGraphVersionId } = useAppStore();

  const { data: vehicles, isLoading: vehiclesLoading } = useQuery({
    queryKey: ["vehicles", currentProjectId],
    queryFn: () => vehiclesApi.list(currentProjectId!),
    enabled: !!currentProjectId,
  });
  const { data: customers, isLoading: customersLoading } = useQuery({
    queryKey: ["customers", currentProjectId],
    queryFn: () => customersApi.list(currentProjectId!),
    enabled: !!currentProjectId,
  });
  const { data: depots } = useQuery({
    queryKey: ["depots", currentProjectId],
    queryFn: () => depotsApi.list(currentProjectId!),
    enabled: !!currentProjectId,
  });
  const { data: jobs, isLoading: jobsLoading } = useQuery({
    queryKey: ["optimization-jobs", currentProjectId],
    queryFn: () => optimizationApi.list(currentProjectId!),
    enabled: !!currentProjectId,
  });
  const { data: graphVersion } = useQuery({
    queryKey: ["graph-version", currentGraphVersionId],
    queryFn: () => graphsApi.get(currentGraphVersionId!),
    enabled: !!currentGraphVersionId,
  });
  const { data: topology } = useQuery({
    queryKey: ["graph-topology", currentGraphVersionId],
    queryFn: () => graphsApi.topology(currentGraphVersionId!),
    enabled: !!currentGraphVersionId,
  });

  const latestSucceededJob = jobs?.find((j) => j.status === "succeeded" || j.status === "completed");
  const { data: latestResult, isLoading: resultLoading } = useQuery({
    queryKey: ["optimization-routes", latestSucceededJob?.id],
    queryFn: () => optimizationApi.routes(latestSucceededJob!.id),
    enabled: !!latestSucceededJob,
  });

  const usedVehicles = latestResult?.routes.filter((r) => r.vehicle_id).length ?? 0;
  const utilizationPct = latestResult && vehicles && vehicles.length > 0
    ? Math.round((usedVehicles / vehicles.length) * 100)
    : null;

  return (
    <div className="h-full flex flex-col">
      <div className="px-6 py-4 border-b border-base-800">
        <h1 className="text-lg font-semibold">Operations</h1>
        <p className="text-sm text-ink-500">Live fleet and network status.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 p-4">
        {vehiclesLoading ? <KpiCardSkeleton /> : <KpiCard label="Vehicles" value={vehicles?.length ?? 0} icon={Truck} />}
        {customersLoading ? <KpiCardSkeleton /> : <KpiCard label="Customers" value={customers?.length ?? 0} icon={Users} />}

        {!latestSucceededJob ? (
          <StatusCard label="Distance" text="No completed run" />
        ) : resultLoading ? <KpiCardSkeleton /> : (
          <KpiCard label="Distance" value={(latestResult!.metrics.distance_m / 1000)} decimals={1} suffix=" km" icon={Gauge} />
        )}

        {!latestSucceededJob ? (
          <StatusCard label="Travel Time" text="No completed run" />
        ) : resultLoading ? <KpiCardSkeleton /> : (
          <KpiCard label="Travel Time" value={Math.round(latestResult!.metrics.time_s / 60)} suffix=" min" icon={Clock} />
        )}

        {!latestSucceededJob ? (
          <StatusCard label="Congestion Cost" text="No completed run" />
        ) : resultLoading ? <KpiCardSkeleton /> : (
          <KpiCard label="Congestion Cost" value={latestResult!.metrics.congestion_cost} decimals={1} icon={Flame} />
        )}

        {jobsLoading ? <KpiCardSkeleton /> : <KpiCard label="Optimizations Run" value={jobs?.length ?? 0} icon={Activity} />}

        {utilizationPct === null ? (
          <StatusCard label="Utilization" text="No completed run" />
        ) : (
          <KpiCard label="Utilization" value={utilizationPct} suffix="%" icon={CheckCircle2} />
        )}

        {!currentGraphVersionId ? (
          <StatusCard label="Graph" text="No graph version" />
        ) : !graphVersion ? (
          <KpiCardSkeleton />
        ) : (
          <StatusCard label="Graph" text={graphVersion.is_connected ? "Connected" : "Disconnected"} />
        )}
      </div>

      <div className="flex-1 p-4 pt-0 min-h-0">
        <div className="panel h-full p-2 relative">
          <div className="absolute top-3 right-3 z-10 flex gap-1.5">
            <MapLayerToggle layerKey="traffic" label="Traffic" />
            <MapLayerToggle layerKey="routes" label="Routes" />
            <MapLayerToggle layerKey="customers" label="Customers" />
            <MapLayerToggle layerKey="depots" label="Depots" />
          </div>
          <NetworkMap
            nodes={topology?.nodes ?? []}
            edges={topology?.edges.map((e) => ({ u: e.u, v: e.v })) ?? []}
            depots={depots?.filter((d) => d.latitude != null && d.longitude != null)
              .map((d) => ({ id: d.id, lat: d.latitude!, lon: d.longitude!, name: d.name })) ?? []}
            customers={customers?.filter((c) => c.latitude != null && c.longitude != null)
              .map((c) => ({ id: c.id, lat: c.latitude!, lon: c.longitude! })) ?? []}
            selectedRoutePath={latestResult?.routes[0]?.path}
          />
        </div>
      </div>
    </div>
  );
}
