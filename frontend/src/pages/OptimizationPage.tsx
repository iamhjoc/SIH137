/**
 * Optimization Studio -- the application's signature workspace.
 * Layout: configuration rail | network map | live telemetry footer.
 *
 * The Feasibility Pre-Check panel and the map are both driven by real
 * data fetched for the current project (customers, vehicles, depots,
 * graph version, traffic scenario, topology) -- no hardcoded counts.
 */
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Play, Square, ArrowRight } from "lucide-react";
import { AlgorithmSelector } from "@/components/optimization/AlgorithmSelector";
import { ObjectiveWeightSliders } from "@/components/optimization/ObjectiveWeightSliders";
import { FeasibilityChecklist, type FeasibilityCheck } from "@/components/optimization/FeasibilityChecklist";
import { LiveTelemetry } from "@/components/optimization/LiveTelemetry";
import { ConvergenceChart } from "@/components/optimization/ConvergenceChart";
import { QPSOSwarmVisualization } from "@/components/optimization/QPSOSwarmVisualization";
import { NetworkMap } from "@/components/map/NetworkMap";
import { MapSkeleton } from "@/components/common/Skeletons";
import { useOptimizationJob } from "@/hooks/useOptimizationJob";
import { useAppStore } from "@/store/useAppStore";
import { optimizationApi } from "@/api/optimization";
import { graphsApi } from "@/api/graphs";
import { trafficApi } from "@/api/traffic";
import { vehiclesApi } from "@/api/vehicles";
import { customersApi } from "@/api/customers";
import { depotsApi } from "@/api/depots";
import type { Algorithm, ObjectiveWeights } from "@/types/api";

const DEFAULT_WEIGHTS: ObjectiveWeights = { distance: 0.25, time: 0.4, congestion: 0.25, late: 0.1, vehicle: 0, constraint: 1 };

export function OptimizationPage() {
  const navigate = useNavigate();
  const { currentProjectId, currentGraphVersionId, currentTrafficScenarioId, setLastOptimizationJobId } = useAppStore();
  const [algorithm, setAlgorithm] = useState<Algorithm>("qpso");
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS);
  const [preset, setPreset] = useState<string | null>("Balanced");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const jobState = useOptimizationJob(activeJobId);
  const isRunning = jobState.status === "running" || jobState.status === "connecting";
  const isSucceeded = jobState.status === "succeeded" || jobState.status === "completed";

  const { data: graphVersion } = useQuery({
    queryKey: ["graph-version", currentGraphVersionId],
    queryFn: () => graphsApi.get(currentGraphVersionId!),
    enabled: !!currentGraphVersionId,
  });
  const { data: topology } = useQuery({
    queryKey: ["graph-topology", currentGraphVersionId],
    queryFn: () => graphsApi.topology(currentGraphVersionId!),
    enabled: !!currentGraphVersionId,
  });
  const { data: trafficScenario } = useQuery({
    queryKey: ["traffic-scenario", currentTrafficScenarioId],
    queryFn: () => trafficApi.get(currentTrafficScenarioId!),
    enabled: !!currentTrafficScenarioId,
  });
  const { data: vehicles } = useQuery({
    queryKey: ["vehicles", currentProjectId],
    queryFn: () => vehiclesApi.list(currentProjectId!),
    enabled: !!currentProjectId,
  });
  const { data: customers } = useQuery({
    queryKey: ["customers", currentProjectId],
    queryFn: () => customersApi.list(currentProjectId!),
    enabled: !!currentProjectId,
  });
  const { data: depots } = useQuery({
    queryKey: ["depots", currentProjectId],
    queryFn: () => depotsApi.list(currentProjectId!),
    enabled: !!currentProjectId,
  });

  // Keep useAppStore in sync so RoutesPage (and anything else that wants
  // "the most recent run") can find this job even without a URL param.
  useEffect(() => {
    if (activeJobId) setLastOptimizationJobId(activeJobId);
  }, [activeJobId, setLastOptimizationJobId]);

  const checks: FeasibilityCheck[] = useMemo(() => {
    const totalDemand = customers?.reduce((sum, c) => sum + c.demand_units, 0) ?? 0;
    const totalCapacity = vehicles?.reduce((sum, v) => sum + v.capacity_units, 0) ?? 0;
    const loading = "pending" as const;

    return [
      {
        key: "network",
        label: "Network",
        status: !currentGraphVersionId ? "fail" : !graphVersion ? loading : graphVersion.is_connected ? "pass" : "fail",
        detail: !currentGraphVersionId ? "No graph selected" : graphVersion ? (graphVersion.is_connected ? "Connected" : "Disconnected") : undefined,
      },
      {
        key: "customers",
        label: "Customers",
        status: !customers ? loading : customers.length > 0 ? "pass" : "fail",
        detail: customers ? `${customers.length} valid` : undefined,
      },
      {
        key: "vehicles",
        label: "Vehicles",
        status: !vehicles ? loading : vehicles.length > 0 ? "pass" : "fail",
        detail: vehicles ? `${vehicles.length} available` : undefined,
      },
      {
        key: "capacity",
        label: "Capacity",
        status: (!vehicles || !customers) ? loading : totalCapacity >= totalDemand ? "pass" : "fail",
        detail: (vehicles && customers) ? `${totalCapacity} / ${totalDemand} units` : undefined,
      },
      {
        key: "depot",
        label: "Depot",
        status: !depots ? loading : depots.length > 0 ? "pass" : "fail",
        detail: depots ? `${depots.length} configured` : undefined,
      },
      {
        key: "traffic",
        label: "Traffic",
        status: currentTrafficScenarioId ? (trafficScenario ? "pass" : loading) : "pending",
        detail: currentTrafficScenarioId ? trafficScenario?.name : "Not selected (optional)",
      },
    ];
  }, [currentGraphVersionId, graphVersion, customers, vehicles, depots, currentTrafficScenarioId, trafficScenario]);

  const requiredChecksPass = checks.filter((c) => c.key !== "traffic").every((c) => c.status === "pass");

  async function handleRun() {
    if (!currentProjectId || !currentGraphVersionId || !requiredChecksPass) return;
    const job = await optimizationApi.create(
      {
        project_id: currentProjectId,
        graph_version_id: currentGraphVersionId,
        traffic_scenario_id: currentTrafficScenarioId,
        algorithm,
        seed: 20260909,
        objective_weights: weights,
        algorithm_config: { particles: 40, iterations: 500, beta_start: 1.0, beta_end: 0.5 },
        constraints: { capacity: true, visit_once: true, return_to_depot: true },
      },
      crypto.randomUUID(),
    );
    setActiveJobId(job.id);
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-6 py-4 border-b border-base-800">
        <div>
          <h1 className="text-lg font-semibold">Optimization Studio</h1>
          <p className="text-sm text-ink-500">Configure and run a congestion-aware routing optimization.</p>
        </div>
        <div className="flex items-center gap-2">
          {isSucceeded && activeJobId && (
            <button onClick={() => navigate(`/routes/${activeJobId}`)} className="btn-secondary">
              View Optimized Routes <ArrowRight size={14} />
            </button>
          )}
          <button onClick={handleRun} disabled={isRunning || !requiredChecksPass} className="btn-primary" title={!requiredChecksPass ? "Resolve the failing feasibility checks first" : undefined}>
            {isRunning ? <Square size={14} /> : <Play size={14} />}
            {isRunning ? "Optimizing…" : "Run Optimization"}
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <aside className="w-[300px] shrink-0 border-r border-base-800 overflow-y-auto p-4 space-y-6">
          <AlgorithmSelector value={algorithm} onChange={setAlgorithm} />
          {algorithm === "qpso" && (
            <ObjectiveWeightSliders weights={weights} onChange={setWeights} activePreset={preset} onPresetChange={setPreset} />
          )}
          <div>
            <span className="label-caps mb-2 block">Feasibility Pre-Check</span>
            <FeasibilityChecklist checks={checks} />
          </div>
        </aside>

        <section className="flex-1 relative p-4">
          {isRunning ? (
            <div className="h-full grid grid-rows-[1fr_auto] gap-4">
              <div className="grid grid-cols-2 gap-4 min-h-0">
                <div className="panel p-2 min-h-0">
                  <NetworkMap nodes={topology?.nodes ?? []} edges={topology?.edges.map((e) => ({ u: e.u, v: e.v })) ?? []} />
                </div>
                <div className="panel min-h-0">
                  <QPSOSwarmVisualization convergence={jobState.convergence} />
                </div>
              </div>
            </div>
          ) : (
            <MapSkeleton />
          )}
        </section>
      </div>

      <motion.footer
        initial={false}
        animate={{ height: activeJobId ? "auto" : 0 }}
        className="border-t border-base-800 overflow-hidden shrink-0"
      >
        {activeJobId && (
          <div className="p-4 space-y-4">
            <LiveTelemetry state={jobState} />
            <ConvergenceChart data={jobState.convergence} />
          </div>
        )}
      </motion.footer>
    </div>
  );
}
