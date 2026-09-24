import { api } from "./client";
import type { Algorithm, AggregateMetrics, BenchmarkExperiment, BenchmarkRun } from "@/types/api";

export const benchmarksApi = {
  create: (payload: {
    project_id: string; name: string; graph_version_id: string;
    traffic_scenario_id?: string | null; algorithms: Algorithm[]; repetitions: number; seed: number;
  }) => api.post<BenchmarkExperiment>("/benchmarks", payload),
  list: (projectId: string, limit = 50) =>
    api.get<BenchmarkExperiment[]>(`/benchmarks?project_id=${projectId}&limit=${limit}`),
  get: (id: string) =>
    api.get<{ experiment: BenchmarkExperiment; runs: BenchmarkRun[]; aggregates: Partial<Record<Algorithm, AggregateMetrics>> }>(`/benchmarks/${id}`),
};
