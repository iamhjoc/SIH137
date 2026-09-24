import { api } from "./client";
import type { Vehicle } from "@/types/api";

export const vehiclesApi = {
  list: (projectId: string) => api.get<Vehicle[]>(`/projects/${projectId}/vehicles`),
  create: (projectId: string, payload: {
    code: string; capacity_units: number; fixed_cost?: number; cost_per_km?: number;
    max_route_seconds?: number; start_depot_id: string; end_depot_id: string;
  }) => api.post<Vehicle>(`/projects/${projectId}/vehicles`, payload),
};
