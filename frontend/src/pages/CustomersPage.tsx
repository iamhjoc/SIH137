import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { customersApi } from "@/api/customers";
import { useAppStore } from "@/store/useAppStore";
import { TableSkeleton } from "@/components/common/Skeletons";
import { EmptyState } from "@/components/common/EmptyState";
import { NewCustomerButton } from "@/components/forms/NewCustomerModal";
import { Users, Search } from "lucide-react";

export function CustomersPage() {
  const projectId = useAppStore((s) => s.currentProjectId);
  const [search, setSearch] = useState("");
  const { data: customers, isLoading } = useQuery({
    queryKey: ["customers", projectId],
    queryFn: () => customersApi.list(projectId!),
    enabled: !!projectId,
  });

  const filtered = customers?.filter((c) => c.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="h-full flex">
      <div className="flex-1 p-6 overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-lg font-semibold">Customers</h1>
            <p className="text-sm text-ink-500">Delivery demand and constraints.</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-2.5 text-ink-700" />
              <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search customers…" className="input-field pl-8 w-64" />
            </div>
            {projectId && <NewCustomerButton projectId={projectId} />}
          </div>
        </div>

        {isLoading && <TableSkeleton />}

        {!isLoading && (!filtered || filtered.length === 0) && (
          <EmptyState
            title="NO CUSTOMERS"
            description="Import or add customers to define delivery demand for this project."
            icon={<Users size={28} />}
          />
        )}

        {filtered && filtered.length > 0 && (
          <div className="panel overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-base-700 text-left">
                  <th className="label-caps px-4 py-3">Ref</th>
                  <th className="label-caps px-4 py-3">Name</th>
                  <th className="label-caps px-4 py-3">Demand</th>
                  <th className="label-caps px-4 py-3">Priority</th>
                  <th className="label-caps px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => (
                  <tr key={c.id} className="border-b border-base-800 last:border-0 hover:bg-base-900/50 cursor-pointer">
                    <td className="px-4 py-2.5 text-ink-500 font-mono text-xs">{c.external_ref}</td>
                    <td className="px-4 py-2.5 font-medium">{c.name}</td>
                    <td className="px-4 py-2.5 tabular-nums">{c.demand_units}</td>
                    <td className="px-4 py-2.5 tabular-nums">{c.priority ?? "—"}</td>
                    <td className="px-4 py-2.5 capitalize text-traffic-normal">{c.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
