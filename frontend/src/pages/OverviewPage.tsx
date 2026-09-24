/**
 * "Urban Mobility Command Center" -- entry dashboard. Every number here is
 * fetched from the real API for whatever project is currently selected
 * (see the context selector in the top bar) -- there is no mock/sample
 * data. If nothing is real yet for this project (no jobs run, no traffic
 * scenario chosen), the affected card says so instead of showing a
 * plausible-looking fake number.
 */
import { motion } from "framer-motion";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Sparkles, Truck, Users, Gauge, Activity, FolderKanban } from "lucide-react";
import { KpiCard } from "@/components/kpi/KpiCard";
import { KpiCardSkeleton } from "@/components/common/Skeletons";
import { EmptyState } from "@/components/common/EmptyState";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { useAppStore } from "@/store/useAppStore";
import { projectsApi } from "@/api/projects";
import { graphsApi } from "@/api/graphs";
import { trafficApi } from "@/api/traffic";
import { vehiclesApi } from "@/api/vehicles";
import { customersApi } from "@/api/customers";
import { optimizationApi } from "@/api/optimization";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

/** Lightweight, dependency-free animated network motif: pulsing nodes with
 *  flowing edges, built as inline SVG so it costs almost nothing on the
 *  landing screen and never distracts from the content in front of it.
 *  Purely decorative -- not meant to represent this project's actual
 *  network, so it isn't part of the "real vs fake data" concern. */
function NetworkMotif() {
  const reducedMotion = useReducedMotion();
  const nodes = useMemo(
    () => Array.from({ length: 14 }, (_, i) => ({
      x: (i * 137) % 100,
      y: (i * 89) % 100,
      delay: (i % 5) * 0.4,
    })),
    [],
  );

  return (
    <svg className="absolute inset-0 h-full w-full opacity-[0.35]" preserveAspectRatio="none" aria-hidden="true">
      {nodes.map((n, i) =>
        nodes.slice(i + 1, i + 3).map((m, j) => (
          <line
            key={`${i}-${j}`}
            x1={`${n.x}%`} y1={`${n.y}%`} x2={`${m.x}%`} y2={`${m.y}%`}
            stroke="#2e333c" strokeWidth={1}
          />
        )),
      )}
      {nodes.map((n, i) => (
        <circle
          key={i}
          cx={`${n.x}%`} cy={`${n.y}%`} r={2.5}
          fill="#5eead4"
          className={reducedMotion ? "" : "animate-pulse-node"}
          style={{ animationDelay: `${n.delay}s` }}
        />
      ))}
    </svg>
  );
}

export function OverviewPage() {
  const { currentProjectId, currentGraphVersionId, currentTrafficScenarioId } = useAppStore();

  const { data: project } = useQuery({
    queryKey: ["project", currentProjectId],
    queryFn: () => projectsApi.get(currentProjectId!),
    enabled: !!currentProjectId,
  });
  const { data: graphVersion } = useQuery({
    queryKey: ["graph-version", currentGraphVersionId],
    queryFn: () => graphsApi.get(currentGraphVersionId!),
    enabled: !!currentGraphVersionId,
  });
  const { data: trafficScenario } = useQuery({
    queryKey: ["traffic-scenario", currentTrafficScenarioId],
    queryFn: () => trafficApi.get(currentTrafficScenarioId!),
    enabled: !!currentTrafficScenarioId,
  });
  const { data: trafficEdges } = useQuery({
    queryKey: ["traffic-edges", currentTrafficScenarioId],
    queryFn: () => trafficApi.edges(currentTrafficScenarioId!),
    enabled: !!currentTrafficScenarioId,
  });
  const { data: vehicles, isLoading: vehiclesLoading } = useQuery({
    queryKey: ["vehicles", currentProjectId],
    queryFn: () => vehiclesApi.list(currentProjectId!),
    enabled: !!currentProjectId,
  });
  const { data: customers, isLoading: customersLoading } = useQuery({
    queryKey: ["customers", currentProjectId],
    queryFn: () => customersApi.list(currentProjectId!),
    enabled: !!currentProjectId,
  });
  const { data: jobs, isLoading: jobsLoading } = useQuery({
    queryKey: ["optimization-jobs", currentProjectId],
    queryFn: () => optimizationApi.list(currentProjectId!),
    enabled: !!currentProjectId,
  });

  const activeJobs = jobs?.filter((j) => j.status === "queued" || j.status === "running").length;
  // congestion_factor: 1.0 = free flow, lower = worse congestion. Shown
  // here as "average speed reduction vs. free flow".
  const avgCongestionPct = trafficEdges && trafficEdges.length > 0
    ? Math.round((1 - (trafficEdges.reduce((sum, e) => sum + e.congestion_factor, 0) / trafficEdges.length)) * 100)
    : null;

  const subtitle = currentProjectId
    ? [
        project?.name ?? "\u2026",
        graphVersion ? `Network v${graphVersion.version_no}` : "No graph version selected",
        trafficScenario ? `Traffic scenario: ${trafficScenario.name}` : "No traffic scenario selected",
      ].join(" \u00b7 ")
    : "No project selected";

  return (
    <div className="relative h-full overflow-y-auto">
      <div className="relative h-[280px] border-b border-base-800 overflow-hidden flex items-end">
        <NetworkMotif />
        <div className="relative z-10 p-8 w-full">
          <p className="text-sm text-ink-500 mb-1">{greeting()}</p>
          <motion.h1
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-3xl font-semibold tracking-tight mb-1"
          >
            Urban Mobility Command Center
          </motion.h1>
          <p className="text-ink-500 mb-5">{subtitle}</p>
          {currentProjectId && (
            <Link to="/optimization" className="btn-primary w-fit">
              <Sparkles size={14} /> Optimize Routes
            </Link>
          )}
        </div>
      </div>

      {!currentProjectId ? (
        <div className="p-8">
          <EmptyState
            title="NO PROJECT SELECTED"
            description="Choose a project from the selector in the top bar, or create a new one, to see its live stats here."
            icon={<FolderKanban size={28} />}
          />
        </div>
      ) : (
        <div className="p-8 grid grid-cols-2 md:grid-cols-4 gap-4">
          {jobsLoading ? <KpiCardSkeleton /> : <KpiCard label="Active Jobs" value={activeJobs ?? 0} icon={Activity} />}
          {vehiclesLoading ? <KpiCardSkeleton /> : <KpiCard label="Vehicles" value={vehicles?.length ?? 0} icon={Truck} />}
          {customersLoading ? <KpiCardSkeleton /> : <KpiCard label="Customers" value={customers?.length ?? 0} icon={Users} />}
          {currentTrafficScenarioId ? (
            avgCongestionPct === null ? (
              <KpiCardSkeleton />
            ) : (
              <KpiCard label="Congestion" value={avgCongestionPct} suffix="%" icon={Gauge} />
            )
          ) : (
            <div className="panel p-4 flex flex-col justify-center gap-1">
              <span className="label-caps">Congestion</span>
              <span className="text-sm text-ink-500">No traffic scenario</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
