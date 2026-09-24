import { AnimatedNumber } from "@/components/kpi/AnimatedNumber";
import type { OptimizationJobState } from "@/hooks/useOptimizationJob";

function formatRuntime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function LiveTelemetry({ state }: { state: OptimizationJobState }) {
  const improvementPct =
    state.convergence.length > 1 && state.convergence[0].bestCost > 0
      ? ((state.convergence[0].bestCost - (state.bestCost ?? state.convergence[0].bestCost)) / state.convergence[0].bestCost) * 100
      : 0;

  return (
    <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
      <Metric label="Iteration" value={`${state.iteration} / ${state.totalIterations || "—"}`} />
      <Metric label="Best Cost" value={state.bestCost !== null ? <AnimatedNumber value={state.bestCost} decimals={2} /> : "—"} />
      <Metric label="Improvement" value={<span className="text-traffic-normal">↓ {improvementPct.toFixed(1)}%</span>} />
      <Metric label="Particles" value="—" />
      <Metric label="Runtime" value={formatRuntime(state.runtimeMs)} />
      <Metric
        label="Status"
        value={
          <span className="capitalize">
            {state.status === "running" ? "Searching…" : state.status}
          </span>
        }
      />
    </div>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="label-caps mb-1">{label}</p>
      <p className="text-lg font-semibold tabular-nums">{value}</p>
    </div>
  );
}
