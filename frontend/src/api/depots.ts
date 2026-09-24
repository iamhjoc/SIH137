import { api } from "./client";
import type { Depot } from "@/types/api";

export const depotsApi = {
  list: (projectId: string) => api.get<Depot[]>(`/projects/${projectId}/depots`),
  create: (projectId: string, payload: {
    name: string; latitude: number; longitude: number;
    open_time?: string | null; close_time?: string | null;
  }) => api.post<Depot>(`/projects/${projectId}/depots`, payload),
  get: (id: string) => api.get<Depot>(`/depots/${id}`),
};
