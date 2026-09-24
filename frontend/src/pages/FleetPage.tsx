import { useQuery } from "@tanstack/react-query";
import { vehiclesApi } from "@/api/vehicles";
import { useAppStore } from "@/store/useAppStore";
import { TableSkeleton } from "@/components/common/Skeletons";
import { EmptyState } from "@/components/common/EmptyState";
import { NewVehicleButton } from "@/components/forms/NewVehicleModal";
import { Truck } from "lucide-react";

export function FleetPage() {
  const projectId = useAppStore((s) => s.currentProjectId);
  const { data: vehicles, isLoading } = useQuery({
    queryKey: ["vehicles", projectId],
    queryFn: () => vehiclesApi.list(projectId!),
    enabled: !!projectId,
  });

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-lg font-semibold">Fleet</h1>
        {projectId && <NewVehicleButton projectId={projectId} />}
      </div>
      <p className="text-sm text-ink-500 mb-4">Vehicle capacity, cost, and depot assignment.</p>

      {isLoading && <TableSkeleton />}

      {!isLoading && (!vehicles || vehicles.length === 0) && (
        <EmptyState title="NO VEHICLES" description="Add vehicles to build a fleet capable of serving your customer demand." icon={<Truck size={28} />} />
      )}

      {vehicles && vehicles.length > 0 && (
        <div className="panel overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-base-700 text-left">
                <th className="label-caps px-4 py-3">Code</th>
                <th className="label-caps px-4 py-3">Capacity</th>
                <th className="label-caps px-4 py-3">Fixed Cost</th>
                <th className="label-caps px-4 py-3">Cost / km</th>
                <th className="label-caps px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {vehicles.map((v) => (
                <tr key={v.id} className="border-b border-base-800 last:border-0 hover:bg-base-900/50">
                  <td className="px-4 py-2.5 font-medium">{v.code}</td>
                  <td className="px-4 py-2.5 tabular-nums">{v.capacity_units}</td>
                  <td className="px-4 py-2.5 tabular-nums">₹{v.fixed_cost?.toFixed(0)}</td>
                  <td className="px-4 py-2.5 tabular-nums">₹{v.cost_per_km?.toFixed(1)}</td>
                  <td className="px-4 py-2.5 capitalize text-traffic-normal">{v.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
