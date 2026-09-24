/**
 * Experiments and Benchmarks are the same backend concept
 * (BenchmarkExperiment) -- this page just points at where experiments
 * are actually created and viewed, rather than duplicating that UI or
 * (as before) having a button that did nothing.
 */
import { useNavigate } from "react-router-dom";
import { EmptyState } from "@/components/common/EmptyState";
import { FlaskConical } from "lucide-react";

export function ExperimentsPage() {
  const navigate = useNavigate();
  return (
    <div className="p-6 h-full">
      <h1 className="text-lg font-semibold mb-1">Experiments</h1>
      <p className="text-sm text-ink-500 mb-4">Repeated, seeded benchmark experiments and their statistical results.</p>
      <EmptyState
        title="MANAGED ON THE BENCHMARKS PAGE"
        description="Experiments and benchmarks are the same thing here -- create and compare QPSO against classical baselines across repeated, seeded trials there."
        icon={<FlaskConical size={28} />}
        action={{ label: "Go to Benchmarks", onClick: () => navigate("/benchmarks") }}
      />
    </div>
  );
}
