import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Modal } from "@/components/common/Modal";
import { customersApi } from "@/api/customers";
import { ApiError } from "@/api/client";

export function NewCustomerButton({ projectId }: { projectId: string }) {
  const [open, setOpen] = useState(false);
  const [externalRef, setExternalRef] = useState("");
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [demandUnits, setDemandUnits] = useState("1");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      customersApi.create(projectId, {
        external_ref: externalRef.trim(),
        name: name.trim(),
        address: address.trim(),
        demand_units: Number(demandUnits) || 1,
      }),
    onSuccess: () => {
      // Matches both ["customers", projectId] (CustomersPage) and
      // ["customers", projectId, "map"] (NetworkPage) via prefix match.
      queryClient.invalidateQueries({ queryKey: ["customers", projectId] });
      setOpen(false);
      setExternalRef("");
      setName("");
      setAddress("");
      setDemandUnits("1");
    },
  });

  const canSubmit = externalRef.trim() && name.trim() && address.trim();

  return (
    <>
      <button onClick={() => setOpen(true)} className="btn-primary flex items-center gap-1.5">
        <Plus size={14} /> Add Customer
      </button>

      <Modal open={open} title="Add Customer" onClose={() => setOpen(false)}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!canSubmit) return;
            mutation.mutate();
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label-caps block mb-1.5" htmlFor="customer-ref">Reference</label>
              <input
                id="customer-ref"
                value={externalRef}
                onChange={(e) => setExternalRef(e.target.value)}
                placeholder="CUST-0142"
                className="input-field w-full"
                autoFocus
                required
              />
            </div>
            <div>
              <label className="label-caps block mb-1.5" htmlFor="customer-demand">Demand</label>
              <input
                id="customer-demand"
                value={demandUnits}
                onChange={(e) => setDemandUnits(e.target.value)}
                inputMode="numeric"
                className="input-field w-full"
              />
            </div>
          </div>
          <div>
            <label className="label-caps block mb-1.5" htmlFor="customer-name">Name</label>
            <input
              id="customer-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Model Town Store"
              className="input-field w-full"
              required
            />
          </div>
          <div>
            <label className="label-caps block mb-1.5" htmlFor="customer-address">Address</label>
            <input
              id="customer-address"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="123 Model Town, Ludhiana, Punjab"
              className="input-field w-full"
              required
            />
            <p className="text-xs text-ink-500 mt-1">Resolved to coordinates server-side via the configured geocoding provider.</p>
          </div>
          {mutation.isError && (
            <p className="text-xs text-traffic-severe">
              {mutation.error instanceof ApiError ? mutation.error.message : "Failed to create customer."}
            </p>
          )}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={() => setOpen(false)} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={mutation.isPending || !canSubmit} className="btn-primary">
              {mutation.isPending ? "Adding…" : "Add Customer"}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
