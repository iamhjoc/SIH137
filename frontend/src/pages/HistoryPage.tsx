/**
 * Decision History -- past optimization runs for the current project,
 * from the real GET /optimization-jobs list endpoint (added alongside
 * this page, since it didn't previously exist). "Inspect" navigates to
 * the real Routes page for a completed run; there is no fabricated
 * runtime/graph/traffic text here -- only fields the job response
 * actually has.
 */
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { History as HistoryIcon } from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";
import { TableSkeleton } from "@/components/common/Skeletons";
import { useAppStore } from "@/store/useAppStore";
import { optimizationApi } from "@/api/optimization";

function formatWhen(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export function HistoryPage() {
  const currentProjectId = useAppStore((s) => s.currentProjectId);
  const { data: jobs, isLoading } = useQuery({
    queryKey: ["optimization-jobs", currentProjectId],
    queryFn: () => optimizationApi.list(currentProjectId!),
    enabled: !!currentProjectId,
  });

  return (
    <div className="p-6">
      <h1 className="text-lg font-semibold mb-1">Decision History</h1>
      <p className="text-sm text-ink-500 mb-4">Optimization runs for the current project, most recent first.</p>

      {!currentProjectId ? (
        <EmptyState title="NO PROJECT SELECTED" description="Select a project to see its run history." icon={<HistoryIcon size={28} />} />
      ) : isLoading ? (
        <TableSkeleton />
      ) : !jobs || jobs.length === 0 ? (
        <EmptyState title="NO RUNS YET" description="Runs from the Optimization Studio will show up here." icon={<HistoryIcon size={28} />} />
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => (
            <div key={job.id} className="panel p-4 flex items-center justify-between">
              <div>
                <p className="font-medium text-sm uppercase">{job.algorithm}</p>
                <p className="text-xs text-ink-500 mt-1">
                  {formatWhen(job.created_at)} &middot; Seed: {job.seed} &middot; Status:{" "}
                  <span className="capitalize">{job.status}</span>
                  {job.best_cost != null && <> &middot; Best cost: {job.best_cost.toFixed(1)}</>}
                </p>
              </div>
              {(job.status === "succeeded" || job.status === "completed") ? (
                <Link to={`/routes/${job.id}`} className="btn-secondary text-xs">Inspect</Link>
              ) : (
                <span className="text-xs text-ink-700 capitalize">{job.status}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
