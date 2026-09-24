import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Modal } from "@/components/common/Modal";
import { vehiclesApi } from "@/api/vehicles";
import { depotsApi } from "@/api/depots";
import { ApiError } from "@/api/client";

export function NewVehicleButton({ projectId }: { projectId: string }) {
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");
  const [capacity, setCapacity] = useState("");
  const [fixedCost, setFixedCost] = useState("0");
  const [costPerKm, setCostPerKm] = useState("0");
  const [startDepotId, setStartDepotId] = useState("");
  const [endDepotId, setEndDepotId] = useState("");
  const queryClient = useQueryClient();

  const { data: depots } = useQuery({
    queryKey: ["depots", projectId],
    queryFn: () => depotsApi.list(projectId),
    enabled: open,
  });

  const mutation = useMutation({
    mutationFn: () =>
      vehiclesApi.create(projectId, {
        code: code.trim(),
        capacity_units: Number(capacity),
        fixed_cost: Number(fixedCost) || 0,
        cost_per_km: Number(costPerKm) || 0,
        start_depot_id: startDepotId,
        end_depot_id: endDepotId,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vehicles", projectId] });
      setOpen(false);
      setCode("");
      setCapacity("");
      setFixedCost("0");
      setCostPerKm("0");
      setStartDepotId("");
      setEndDepotId("");
    },
  });

  const canSubmit = code.trim() && capacity !== "" && !Number.isNaN(Number(capacity)) && startDepotId && endDepotId;
  const noDepots = depots !== undefined && depots.length === 0;

  return (
    <>
      <button onClick={() => setOpen(true)} className="btn-primary flex items-center gap-1.5">
        <Plus size={14} /> Add Vehicle
      </button>

      <Modal open={open} title="Add Vehicle" onClose={() => setOpen(false)}>
        {noDepots ? (
          <p className="text-sm text-ink-500">
            This project has no depots yet. Add a depot first (on the Network page) — every
            vehicle needs a start and end depot.
          </p>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!canSubmit) return;
              mutation.mutate();
            }}
            className="space-y-4"
          >
            <div>
              <label className="label-caps block mb-1.5" htmlFor="vehicle-code">Code</label>
              <input
                id="vehicle-code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="e.g. VAN-014"
                className="input-field w-full"
                autoFocus
                required
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="label-caps block mb-1.5" htmlFor="vehicle-capacity">Capacity</label>
                <input
                  id="vehicle-capacity"
                  value={capacity}
                  onChange={(e) => setCapacity(e.target.value)}
                  placeholder="500"
                  inputMode="numeric"
                  className="input-field w-full"
                  required
                />
              </div>
              <div>
                <label className="label-caps block mb-1.5" htmlFor="vehicle-fixed-cost">Fixed cost</label>
                <input
                  id="vehicle-fixed-cost"
                  value={fixedCost}
                  onChange={(e) => setFixedCost(e.target.value)}
                  inputMode="decimal"
                  className="input-field w-full"
                />
              </div>
              <div>
                <label className="label-caps block mb-1.5" htmlFor="vehicle-cost-km">Cost / km</label>
                <input
                  id="vehicle-cost-km"
                  value={costPerKm}
                  onChange={(e) => setCostPerKm(e.target.value)}
                  inputMode="decimal"
                  className="input-field w-full"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label-caps block mb-1.5" htmlFor="vehicle-start-depot">Start depot</label>
                <select
                  id="vehicle-start-depot"
                  value={startDepotId}
                  onChange={(e) => setStartDepotId(e.target.value)}
                  className="input-field w-full"
                  required
                >
                  <option value="">Select…</option>
                  {depots?.map((d) => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label-caps block mb-1.5" htmlFor="vehicle-end-depot">End depot</label>
                <select
                  id="vehicle-end-depot"
                  value={endDepotId}
                  onChange={(e) => setEndDepotId(e.target.value)}
                  className="input-field w-full"
                  required
                >
                  <option value="">Select…</option>
                  {depots?.map((d) => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
              </div>
            </div>
            {mutation.isError && (
              <p className="text-xs text-traffic-severe">
                {mutation.error instanceof ApiError ? mutation.error.message : "Failed to create vehicle."}
              </p>
            )}
            <div className="flex justify-end gap-2 pt-1">
              <button type="button" onClick={() => setOpen(false)} className="btn-secondary">Cancel</button>
              <button type="submit" disabled={mutation.isPending || !canSubmit} className="btn-primary">
                {mutation.isPending ? "Adding…" : "Add Vehicle"}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </>
  );
}
