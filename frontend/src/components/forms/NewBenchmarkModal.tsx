import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Modal } from "@/components/common/Modal";
import { benchmarksApi } from "@/api/benchmarks";
import { ApiError } from "@/api/client";
import type { Algorithm } from "@/types/api";

const ALL_ALGORITHMS: Algorithm[] = ["qpso", "ga", "aco", "pso", "dijkstra", "astar"];

export function NewBenchmarkButton({
  projectId, graphVersionId, trafficScenarioId,
}: { projectId: string; graphVersionId: string | null; trafficScenarioId: string | null }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [algorithms, setAlgorithms] = useState<Algorithm[]>(["qpso", "dijkstra"]);
  const [repetitions, setRepetitions] = useState("5");
  const [seed, setSeed] = useState("20260909");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      benchmarksApi.create({
        project_id: projectId,
        name: name.trim(),
        graph_version_id: graphVersionId!,
        traffic_scenario_id: trafficScenarioId,
        algorithms,
        repetitions: Number(repetitions) || 1,
        seed: Number(seed) || 0,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["benchmarks", projectId] });
      setOpen(false);
      setName("");
      setAlgorithms(["qpso", "dijkstra"]);
    },
  });

  function toggleAlgorithm(alg: Algorithm) {
    setAlgorithms((prev) => (prev.includes(alg) ? prev.filter((a) => a !== alg) : [...prev, alg]));
  }

  const canSubmit = name.trim() && !!graphVersionId && algorithms.length > 0;

  return (
    <>
      <button onClick={() => setOpen(true)} className="btn-primary flex items-center gap-1.5">
        <Plus size={14} /> Run Benchmark
      </button>

      <Modal open={open} title="Run Benchmark" onClose={() => setOpen(false)}>
        {!graphVersionId ? (
          <p className="text-sm text-ink-500">This project has no graph version yet -- a benchmark needs one to run algorithms against.</p>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (canSubmit) mutation.mutate();
            }}
            className="space-y-4"
          >
            <div>
              <label className="label-caps block mb-1.5" htmlFor="benchmark-name">Name</label>
              <input
                id="benchmark-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. QPSO vs baselines -- morning peak"
                className="input-field w-full"
                autoFocus
                required
              />
            </div>

            <div>
              <label className="label-caps block mb-1.5">Algorithms</label>
              <div className="flex flex-wrap gap-1.5">
                {ALL_ALGORITHMS.map((alg) => (
                  <button
                    key={alg}
                    type="button"
                    onClick={() => toggleAlgorithm(alg)}
                    className={`text-xs px-2.5 py-1 rounded-sm border uppercase transition-colors ${
                      algorithms.includes(alg) ? "border-signal/40 bg-signal/10 text-signal" : "border-base-600 text-ink-500 hover:text-ink-100"
                    }`}
                  >
                    {alg}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label-caps block mb-1.5" htmlFor="benchmark-reps">Repetitions</label>
                <input
                  id="benchmark-reps"
                  value={repetitions}
                  onChange={(e) => setRepetitions(e.target.value)}
                  inputMode="numeric"
                  className="input-field w-full"
                />
              </div>
              <div>
                <label className="label-caps block mb-1.5" htmlFor="benchmark-seed">Seed</label>
                <input
                  id="benchmark-seed"
                  value={seed}
                  onChange={(e) => setSeed(e.target.value)}
                  inputMode="numeric"
                  className="input-field w-full"
                />
              </div>
            </div>

            {!trafficScenarioId && (
              <p className="text-xs text-ink-500">No traffic scenario selected -- benchmark will run without congestion factors.</p>
            )}

            {mutation.isError && (
              <p className="text-xs text-traffic-severe">
                {mutation.error instanceof ApiError ? mutation.error.message : "Failed to start benchmark."}
              </p>
            )}
            <div className="flex justify-end gap-2 pt-1">
              <button type="button" onClick={() => setOpen(false)} className="btn-secondary">Cancel</button>
              <button type="submit" disabled={mutation.isPending || !canSubmit} className="btn-primary">
                {mutation.isPending ? "Starting…" : "Run Benchmark"}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </>
  );
}
