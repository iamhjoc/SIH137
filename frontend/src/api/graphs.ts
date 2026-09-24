import { api } from "./client";
import type { GraphTopology, GraphVersion } from "@/types/api";

export const graphsApi = {
  get: (id: string) => api.get<GraphVersion>(`/graphs/${id}`),
  topology: (id: string) => api.get<GraphTopology>(`/graphs/${id}/topology`),
  import: (projectId: string, seed: number, rows = 10, cols = 10) =>
    api.post<GraphVersion>("/graphs/import", { project_id: projectId, seed, rows, cols }),
  validate: (id: string) => api.post<{ status: string }>(`/graphs/${id}/validate`),
};
