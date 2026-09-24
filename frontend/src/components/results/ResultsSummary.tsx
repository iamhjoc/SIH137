import { motion } from "framer-motion";
import { KpiCard } from "@/components/kpi/KpiCard";
import { Clock, Gauge, Flame, Truck } from "lucide-react";
import type { OptimizationResultResponse } from "@/types/api";

export function ResultsSummary({ result, baselineCost }: { result: OptimizationResultResponse; baselineCost?: number }) {
  const improvementPct = baselineCost ? ((baselineCost - result.metrics.objective_cost) / baselineCost) * 100 : null;

  return (
    <div>
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mb-4">
        <p className="label-caps mb-1">Optimization Complete</p>
        {improvementPct !== null && (
          <p className="text-3xl font-semibold text-traffic-normal">{improvementPct.toFixed(1)}% improvement</p>
        )}
      </motion.div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Distance" value={result.metrics.distance_m / 1000} decimals={1} suffix=" km" icon={Gauge} />
        <KpiCard label="Travel Time" value={result.metrics.time_s / 60} decimals={0} suffix=" min" icon={Clock} />
        <KpiCard label="Congestion Cost" value={result.metrics.congestion_cost} decimals={1} icon={Flame} />
        <KpiCard label="Vehicles Used" value={result.routes.length} icon={Truck} />
      </div>
    </div>
  );
}
