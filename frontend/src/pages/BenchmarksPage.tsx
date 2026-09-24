/**
 * Benchmarks -- QPSO compared against classical baselines. Experiment
 * list and comparison table are both real: /benchmarks?project_id=...
 * for past experiments, /benchmarks/{id} for that experiment's real
 * per-algorithm aggregates (computed server-side by the previously-
 * unused app/benchmarks/metrics.aggregate() helper, not reimplemented
 * here). No fabricated numbers.
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FlaskConical } from "lucide-react";
import { AlgorithmComparisonTable } from "@/components/comparison/AlgorithmComparisonTable";
import { NewBenchmarkButton } from "@/components/forms/NewBenchmarkModal";
import { EmptyState } from "@/components/common/EmptyState";
import { TableSkeleton } from "@/components/common/Skeletons";
import { useAppStore } from "@/store/useAppStore";
import { benchmarksApi } from "@/api/benchmarks";

export function BenchmarksPage() {
  const { currentProjectId, currentGraphVersionId, currentTrafficScenarioId } = useAppStore();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: experiments, isLoading: experimentsLoading } = useQuery({
    queryKey: ["benchmarks", currentProjectId],
    queryFn: () => benchmarksApi.list(currentProjectId!),
    enabled: !!currentProjectId,
  });

  const activeId = selectedId ?? experiments?.[0]?.id ?? null;
  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ["benchmark-detail", activeId],
    queryFn: () => benchmarksApi.get(activeId!),
    enabled: !!activeId,
    // Experiments run async via Celery -- poll while still queued/running
    // so the table appears as soon as results land, without a refresh.
    refetchInterval: (query) => (query.state.data?.experiment.status === "completed" ? false : 2000),
  });

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-lg font-semibold">Benchmarks</h1>
        {currentProjectId && (
          <NewBenchmarkButton
            projectId={currentProjectId}
            graphVersionId={currentGraphVersionId}
            trafficScenarioId={currentTrafficScenarioId}
          />
        )}
      </div>
      <p className="text-sm text-ink-500 mb-4">
        QPSO compared against classical baselines under identical seed, data, and constraints. No single
        algorithm is declared universally best -- inspect the trade-offs.
      </p>

      {!currentProjectId ? (
        <EmptyState title="NO PROJECT SELECTED" description="Select a project to run or view benchmarks." icon={<FlaskConical size={28} />} />
      ) : experimentsLoading ? (
        <TableSkeleton />
      ) : !experiments || experiments.length === 0 ? (
        <EmptyState title="NO BENCHMARKS YET" description="Run QPSO against classical baselines under identical conditions to compare them." icon={<FlaskConical size={28} />} />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-1.5">
            {experiments.map((exp) => (
              <button
                key={exp.id}
                onClick={() => setSelectedId(exp.id)}
                className={`text-xs px-2.5 py-1.5 rounded-sm border transition-colors ${
                  exp.id === activeId ? "border-signal/40 bg-signal/10 text-signal" : "border-base-600 text-ink-500 hover:text-ink-100"
                }`}
              >
                {exp.name} <span className="text-ink-700">&middot; {exp.status}</span>
              </button>
            ))}
          </div>

          {detailLoading ? (
            <TableSkeleton />
          ) : detail?.experiment.status !== "completed" ? (
            <div className="panel p-4 text-sm text-ink-500">
              This benchmark is <span className="capitalize">{detail?.experiment.status}</span> -- results will appear here once it finishes.
            </div>
          ) : (
            <AlgorithmComparisonTable results={detail.aggregates} />
          )}
        </div>
      )}
    </div>
  );
}
