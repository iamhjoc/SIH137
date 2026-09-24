/**
 * Typed models mirroring the SIH26137 backend contract (/api/v1).
 * Kept in lockstep with app/schemas/* and app/db/models/* on the backend --
 * do not invent fields the API does not return.
 */

export type Role = "ADMIN" | "MANAGER" | "DISPATCHER" | "ANALYST" | "VIEWER";

export type Algorithm = "qpso" | "ga" | "aco" | "pso" | "dijkstra" | "astar";

export type OptimizationJobStatus =
  | "queued" | "running" | "succeeded" | "failed" | "cancelled" | "completed";

export interface User {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  role: Role;
}

export interface Project {
  id: string;
  organization_id: string;
  name: string;
  default_graph_version_id: string | null;
  timezone: string;
  status: "active" | "archived";
  created_at: string;
  updated_at: string;
}

export interface Depot {
  id: string;
  project_id: string;
  name: string;
  status: string;
  latitude?: number;
  longitude?: number;
  open_time?: string | null;
  close_time?: string | null;
}

export interface Customer {
  id: string;
  project_id: string;
  external_ref: string;
  name: string;
  demand_units: number;
  status: string;
  latitude?: number;
  longitude?: number;
  service_seconds?: number;
  window_start?: string | null;
  window_end?: string | null;
  priority?: number;
}

export interface Vehicle {
  id: string;
  project_id: string;
  code: string;
  capacity_units: number;
  fixed_cost?: number;
  cost_per_km?: number;
  max_route_seconds?: number;
  start_depot_id: string;
  end_depot_id: string;
  status: string;
}

export interface GraphVersion {
  id: string;
  project_id: string;
  version_no: number;
  source: string;
  node_count: number;
  edge_count: number;
  is_connected: boolean;
  status: string;
  created_at: string;
}

export interface GraphTopology {
  graph_version_id: string;
  nodes: { id: string; lat: number; lon: number }[];
  edges: { u: string; v: string; length_m: number | null; speed_kmh: number | null }[];
}

export interface TrafficScenario {
  id: string;
  project_id: string;
  name: string;
  kind: "static" | "simulated" | "provider";
  seed: number | null;
  status: string;
}

export interface TrafficEdgeFactor {
  u: string;
  v: string;
  speed_kmh: number;
  congestion_factor: number;
}

export interface ObjectiveWeights {
  distance: number;
  time: number;
  congestion: number;
  late: number;
  vehicle: number;
  constraint: number;
}

export interface AlgorithmConfig {
  particles: number;
  iterations: number;
  beta_start: number;
  beta_end: number;
  time_budget_s?: number | null;
  target_cost?: number | null;
  convergence_threshold?: number | null;
}

export interface OptimizationConstraints {
  capacity: boolean;
  visit_once: boolean;
  return_to_depot: boolean;
}

export interface OptimizationJobCreateRequest {
  project_id: string;
  graph_version_id: string;
  traffic_scenario_id: string | null;
  algorithm: Algorithm;
  seed: number;
  objective_weights: ObjectiveWeights;
  algorithm_config: AlgorithmConfig;
  constraints: OptimizationConstraints;
}

export interface OptimizationJob {
  id: string;
  project_id: string;
  status: OptimizationJobStatus;
  algorithm: Algorithm;
  algorithm_version: string;
  seed: number;
  best_cost: number | null;
  created_at: string;
}

export interface OptimizationProgress {
  job_id: string;
  status: OptimizationJobStatus;
  progress: number;
  iteration: number;
  total_iterations: number;
  best_cost: number | null;
  elapsed_ms: number;
}

export interface RouteStopSummary {
  sequence_no: number;
  stop_type: "depot_start" | "customer" | "depot_end";
  latitude?: number | null;
  longitude?: number | null;
  eta_seconds?: number;
}

export interface RouteSummary {
  vehicle_id: string | null;
  sequence_no: number;
  distance_m: number;
  time_s: number;
  load_units: number;
  /** [lon, lat] pairs tracing the actual road geometry for this vehicle. */
  path?: [number, number][];
  stops: RouteStopSummary[];
}

export interface OptimizationResultResponse {
  job_id: string;
  status: OptimizationJobStatus;
  metrics: {
    distance_m: number;
    time_s: number;
    congestion_cost: number;
    objective_cost: number;
  };
  routes: RouteSummary[];
  provenance: {
    seed: number;
    graph_version: string;
    algorithm_version: string;
  };
}

export interface FeasibilityCheckResult {
  feasible: boolean;
  errors: string[];
}

export interface BenchmarkExperiment {
  id: string;
  project_id: string;
  name: string;
  algorithms: Algorithm[];
  repetitions: number;
  seed: number;
  status: string;
  created_at: string;
}

export interface BenchmarkRun {
  id: string;
  experiment_id: string;
  algorithm: Algorithm;
  objective_cost: number;
  distance_m: number;
  travel_time_s: number;
  congestion_cost: number;
  runtime_ms: number;
  feasible: boolean;
  iterations: number;
}

export interface AggregateMetrics {
  mean_cost: number;
  std_cost: number;
  best_cost: number;
  worst_cost: number;
  mean_runtime_ms: number;
  mean_distance_m: number;
  mean_travel_time_s: number;
  mean_congestion_cost: number;
  feasibility_rate: number;
  mean_iterations: number;
}

export interface ApiErrorEnvelope {
  code: string;
  message: string;
  details: Record<string, unknown>;
  request_id: string;
}
