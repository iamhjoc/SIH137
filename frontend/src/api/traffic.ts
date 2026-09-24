import { api } from "./client";
import type { TrafficEdgeFactor, TrafficScenario } from "@/types/api";

export const trafficApi = {
  list: (projectId: string) => api.get<TrafficScenario[]>(`/traffic/scenarios?project_id=${projectId}`),
  get: (id: string) => api.get<TrafficScenario>(`/traffic/scenarios/${id}`),
  create: (projectId: string, graphVersionId: string, name: string, seed: number) =>
    api.post<TrafficScenario>("/traffic/scenarios", {
      project_id: projectId, graph_version_id: graphVersionId, name, seed,
    }),
  createLive: (projectId: string, graphVersionId: string, name: string) =>
    api.post<TrafficScenario>("/traffic/scenarios/live", {
      project_id: projectId, graph_version_id: graphVersionId, name,
    }),
  edges: (scenarioId: string, timeBucket = 0) =>
    api.get<TrafficEdgeFactor[]>(`/traffic/scenarios/${scenarioId}/edges?time_bucket=${timeBucket}`),
};
