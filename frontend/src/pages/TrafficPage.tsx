/**
 * Traffic Lab. Scenario cards driven by the real /traffic/scenarios list
 * for the current project; each card's congestion stats come from that
 * scenario's real per-edge factors (/traffic/scenarios/{id}/edges), not
 * fabricated numbers. There is no backend field for "confidence" -- the
 * original mock invented one; it's gone rather than faked.
 */
import { useQuery } from "@tanstack/react-query";
import { TrafficBadge, congestionToState } from "@/components/common/TrafficBadge";
import { EmptyState } from "@/components/common/EmptyState";
import { TableSkeleton } from "@/components/common/Skeletons";
import { NewTrafficScenarioButton } from "@/components/forms/NewTrafficScenarioModal";
import { useAppStore } from "@/store/useAppStore";
import { trafficApi } from "@/api/traffic";
import type { TrafficScenario } from "@/types/api";
import { CloudFog } from "lucide-react";

function ScenarioCard({ scenario }: { scenario: TrafficScenario }) {
  const { data: edges, isLoading } = useQuery({
    queryKey: ["traffic-edges", scenario.id],
    queryFn: () => trafficApi.edges(scenario.id),
  });

  const avgCongestion = edges && edges.length > 0
    ? edges.reduce((sum, e) => sum + e.congestion_factor, 0) / edges.length
    : null;
  // congestion_factor: 1.0 = free flow, lower = worse congestion (see
  // congestionToState below) -- "affected" means noticeably below that.
  const affectedRoads = edges?.filter((e) => e.congestion_factor < 0.98).length ?? 0;

  return (
    <div className="panel p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="font-medium">{scenario.name}</p>
        {avgCongestion !== null && <TrafficBadge state={congestionToState(avgCongestion)} />}
      </div>

      {isLoading ? (
        <TableSkeleton rows={3} />
      ) : (
        <>
          <p className="text-2xl font-semibold mb-1">
            {avgCongestion !== null ? `${Math.round((1 - avgCongestion) * 100)}%` : "—"}
          </p>
          <p className="label-caps mb-3">avg. delay vs. free-flow</p>
          <div className="text-xs text-ink-500 space-y-1">
            <p>{affectedRoads} affected road segments</p>
            <p className="capitalize">{scenario.kind}{scenario.seed != null ? ` \u00b7 seed ${scenario.seed}` : ""}</p>
            <p className="capitalize">{scenario.status}</p>
          </div>
        </>
      )}
    </div>
  );
}

export function TrafficPage() {
  const { currentProjectId, currentGraphVersionId } = useAppStore();
  const { data: scenarios, isLoading } = useQuery({
    queryKey: ["traffic-scenarios", currentProjectId],
    queryFn: () => trafficApi.list(currentProjectId!),
    enabled: !!currentProjectId,
  });

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-lg font-semibold">Traffic Lab</h1>
        {currentProjectId && <NewTrafficScenarioButton projectId={currentProjectId} graphVersionId={currentGraphVersionId} />}
      </div>
      <p className="text-sm text-ink-500 mb-4">Simulated and provider traffic scenarios.</p>

      {!currentProjectId ? (
        <EmptyState title="NO PROJECT SELECTED" description="Select a project to see its traffic scenarios." icon={<CloudFog size={28} />} />
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <TableSkeleton /><TableSkeleton /><TableSkeleton />
        </div>
      ) : !scenarios || scenarios.length === 0 ? (
        <EmptyState title="NO TRAFFIC SCENARIOS" description="Create a simulated or live scenario to see congestion on the map and factor it into optimization runs." icon={<CloudFog size={28} />} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {scenarios.map((s) => <ScenarioCard key={s.id} scenario={s} />)}
        </div>
      )}
    </div>
  );
}
