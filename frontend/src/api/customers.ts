import { api } from "./client";
import type { Customer } from "@/types/api";

export interface CustomerCreatePayload {
  external_ref: string;
  name: string;
  // Provide either latitude+longitude OR address -- if address is given,
  // the backend's configured geocoding provider resolves it server-side.
  latitude?: number;
  longitude?: number;
  address?: string;
  demand_units?: number;
  service_seconds?: number;
  window_start?: string | null;
  window_end?: string | null;
  priority?: number;
}

export const customersApi = {
  list: (projectId: string, limit = 50, cursor?: string) =>
    api.get<Customer[]>(`/projects/${projectId}/customers?limit=${limit}${cursor ? `&cursor=${cursor}` : ""}`),
  create: (projectId: string, payload: CustomerCreatePayload) =>
    api.post<Customer>(`/projects/${projectId}/customers`, payload),
};
