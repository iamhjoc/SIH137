import type { Algorithm } from "@/types/api";
import clsx from "clsx";

const ALGORITHMS: { value: Algorithm; label: string; description: string }[] = [
  { value: "qpso", label: "QPSO", description: "Quantum-behaved PSO (recommended)" },
  { value: "pso", label: "PSO", description: "Classical particle swarm" },
  { value: "ga", label: "GA", description: "Genetic algorithm" },
  { value: "aco", label: "ACO", description: "Ant colony optimization" },
  { value: "dijkstra", label: "Dijkstra", description: "Shortest-path baseline" },
  { value: "astar", label: "A*", description: "Heuristic shortest-path baseline" },
];

interface Props {
  value: Algorithm;
  onChange: (algorithm: Algorithm) => void;
}

export function AlgorithmSelector({ value, onChange }: Props) {
  return (
    <div>
      <span className="label-caps mb-2 block">Algorithm</span>
      <div className="grid grid-cols-2 gap-1.5">
        {ALGORITHMS.map((alg) => (
          <button
            key={alg.value}
            onClick={() => onChange(alg.value)}
            className={clsx(
              "text-left rounded-md border px-2.5 py-2 transition-colors",
              value === alg.value ? "border-signal/50 bg-signal/10" : "border-base-600 hover:border-base-500",
            )}
          >
            <p className={clsx("text-sm font-medium", value === alg.value ? "text-signal" : "text-ink-100")}>{alg.label}</p>
            <p className="text-[11px] text-ink-500 leading-tight mt-0.5">{alg.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
