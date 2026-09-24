import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Modal } from "@/components/common/Modal";
import { trafficApi } from "@/api/traffic";
import { ApiError } from "@/api/client";

export function NewTrafficScenarioButton({ projectId, graphVersionId }: { projectId: string; graphVersionId: string | null }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [kind, setKind] = useState<"simulated" | "live">("simulated");
  const [seed, setSeed] = useState("20260909");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => {
      if (!graphVersionId) throw new Error("No graph version selected for this project.");
      return kind === "simulated"
        ? trafficApi.create(projectId, graphVersionId, name.trim(), Number(seed) || 0)
        : trafficApi.createLive(projectId, graphVersionId, name.trim());
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["traffic-scenarios", projectId] });
      setOpen(false);
      setName("");
      setSeed("20260909");
    },
  });

  const canSubmit = name.trim() && !!graphVersionId;

  return (
    <>
      <button onClick={() => setOpen(true)} className="btn-secondary text-xs flex items-center gap-1.5">
        <Plus size={13} /> Create Custom Scenario
      </button>

      <Modal open={open} title="Create Traffic Scenario" onClose={() => setOpen(false)}>
        {!graphVersionId ? (
          <p className="text-sm text-ink-500">This project has no graph version yet -- a traffic scenario needs one to attach congestion factors to.</p>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (canSubmit) mutation.mutate();
            }}
            className="space-y-4"
          >
            <div>
              <label className="label-caps block mb-1.5" htmlFor="scenario-name">Name</label>
              <input
                id="scenario-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Evening Peak"
                className="input-field w-full"
                autoFocus
                required
              />
            </div>

            <div>
              <label className="label-caps block mb-1.5">Source</label>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setKind("simulated")}
                  className={`text-xs px-2.5 py-1 rounded-sm border transition-colors ${kind === "simulated" ? "border-signal/40 bg-signal/10 text-signal" : "border-base-600 text-ink-500 hover:text-ink-100"}`}
                >
                  Simulated
                </button>
                <button
                  type="button"
                  onClick={() => setKind("live")}
                  className={`text-xs px-2.5 py-1 rounded-sm border transition-colors ${kind === "live" ? "border-signal/40 bg-signal/10 text-signal" : "border-base-600 text-ink-500 hover:text-ink-100"}`}
                >
                  Live provider
                </button>
              </div>
              <p className="text-xs text-ink-500 mt-1.5">
                {kind === "simulated"
                  ? "Deterministic synthetic congestion -- no API key required."
                  : "Pulls current traffic from your configured provider (TomTom/HERE/Mappls) -- requires TRAFFIC_API_KEY on the backend."}
              </p>
            </div>

            {kind === "simulated" && (
              <div>
                <label className="label-caps block mb-1.5" htmlFor="scenario-seed">Seed</label>
                <input
                  id="scenario-seed"
                  value={seed}
                  onChange={(e) => setSeed(e.target.value)}
                  inputMode="numeric"
                  className="input-field w-full"
                />
              </div>
            )}

            {mutation.isError && (
              <p className="text-xs text-traffic-severe">
                {mutation.error instanceof ApiError ? mutation.error.message : "Failed to create scenario."}
              </p>
            )}
            <div className="flex justify-end gap-2 pt-1">
              <button type="button" onClick={() => setOpen(false)} className="btn-secondary">Cancel</button>
              <button type="submit" disabled={mutation.isPending || !canSubmit} className="btn-primary">
                {mutation.isPending ? "Creating…" : "Create Scenario"}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </>
  );
}
