import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Modal } from "@/components/common/Modal";
import { depotsApi } from "@/api/depots";
import { ApiError } from "@/api/client";

export function NewDepotButton({ projectId }: { projectId: string }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      depotsApi.create(projectId, {
        name: name.trim(),
        latitude: Number(latitude),
        longitude: Number(longitude),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["depots", projectId] });
      setOpen(false);
      setName("");
      setLatitude("");
      setLongitude("");
    },
  });

  const canSubmit = name.trim() && latitude !== "" && longitude !== "" && !Number.isNaN(Number(latitude)) && !Number.isNaN(Number(longitude));

  return (
    <>
      <button onClick={() => setOpen(true)} className="btn-secondary w-full mt-4 text-xs flex items-center justify-center gap-1.5">
        <Plus size={13} /> Add Depot
      </button>

      <Modal open={open} title="Add Depot" onClose={() => setOpen(false)}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!canSubmit) return;
            mutation.mutate();
          }}
          className="space-y-4"
        >
          <div>
            <label className="label-caps block mb-1.5" htmlFor="depot-name">Name</label>
            <input
              id="depot-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Central Depot"
              className="input-field w-full"
              autoFocus
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label-caps block mb-1.5" htmlFor="depot-lat">Latitude</label>
              <input
                id="depot-lat"
                value={latitude}
                onChange={(e) => setLatitude(e.target.value)}
                placeholder="30.9010"
                inputMode="decimal"
                className="input-field w-full"
                required
              />
            </div>
            <div>
              <label className="label-caps block mb-1.5" htmlFor="depot-lng">Longitude</label>
              <input
                id="depot-lng"
                value={longitude}
                onChange={(e) => setLongitude(e.target.value)}
                placeholder="75.8573"
                inputMode="decimal"
                className="input-field w-full"
                required
              />
            </div>
          </div>
          <p className="text-xs text-ink-500">
            Coordinates only for now — geocoding an address here is a small follow-up using the
            backend's existing geocoding adapters.
          </p>
          {mutation.isError && (
            <p className="text-xs text-traffic-severe">
              {mutation.error instanceof ApiError ? mutation.error.message : "Failed to create depot."}
            </p>
          )}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={() => setOpen(false)} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={mutation.isPending || !canSubmit} className="btn-primary">
              {mutation.isPending ? "Adding…" : "Add Depot"}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
