/**
 * Route comparison across algorithms (section 19). Deliberately avoids
 * declaring a universal "winner" -- highlights the best value per metric
 * column so trade-offs stay visible.
 */
import type { AggregateMetrics, Algorithm } from "@/types/api";
import clsx from "clsx";

const METRICS: { key: keyof AggregateMetrics; label: string; lowerIsBetter: boolean; format: (v: number) => string }[] = [
  { key: "mean_cost", label: "Objective Cost", lowerIsBetter: true, format: (v) => v.toFixed(1) },
  { key: "mean_distance_m", label: "Distance", lowerIsBetter: true, format: (v) => `${(v / 1000).toFixed(1)} km` },
  { key: "mean_travel_time_s", label: "Travel Time", lowerIsBetter: true, format: (v) => `${Math.round(v / 60)} min` },
  { key: "mean_congestion_cost", label: "Congestion Cost", lowerIsBetter: true, format: (v) => v.toFixed(1) },
  { key: "mean_runtime_ms", label: "Runtime", lowerIsBetter: true, format: (v) => `${(v / 1000).toFixed(1)}s` },
  { key: "feasibility_rate", label: "Feasibility", lowerIsBetter: false, format: (v) => `${Math.round(v * 100)}%` },
];

export function AlgorithmComparisonTable({ results }: { results: Partial<Record<Algorithm, AggregateMetrics>> }) {
  const algorithms = Object.keys(results) as Algorithm[];

  const bestFor = (metricKey: keyof AggregateMetrics, lowerIsBetter: boolean): Algorithm | null => {
    let best: Algorithm | null = null;
    let bestVal = lowerIsBetter ? Infinity : -Infinity;
    for (const alg of algorithms) {
      const v = results[alg]?.[metricKey];
      if (v === undefined) continue;
      if ((lowerIsBetter && v < bestVal) || (!lowerIsBetter && v > bestVal)) {
        best = alg;
        bestVal = v;
      }
    }
    return best;
  };

  return (
    <div className="panel overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-base-700">
            <th className="text-left label-caps px-4 py-3">Metric</th>
            {algorithms.map((alg) => (
              <th key={alg} className="text-right label-caps px-4 py-3 uppercase">{alg}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {METRICS.map(({ key, label, lowerIsBetter, format }) => {
            const winner = bestFor(key, lowerIsBetter);
            return (
              <tr key={key} className="border-b border-base-800 last:border-0">
                <td className="px-4 py-2.5 text-ink-500">{label}</td>
                {algorithms.map((alg) => {
                  const value = results[alg]?.[key];
                  return (
                    <td
                      key={alg}
                      className={clsx(
                        "px-4 py-2.5 text-right tabular-nums",
                        alg === winner ? "text-signal font-medium" : "text-ink-300",
                      )}
                    >
                      {value !== undefined ? format(value) : "—"}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
