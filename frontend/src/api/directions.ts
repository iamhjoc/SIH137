import { api } from "./client";

export interface DirectionsPointInput {
  address?: string;
  lat?: number;
  lon?: number;
}

export interface DirectionsRequestPayload {
  origin: DirectionsPointInput;
  destination: DirectionsPointInput;
  criterion: "time" | "distance";
  alternates?: boolean;
}

export interface ResolvedPoint {
  lat: number;
  lon: number;
  label: string;
}

export interface RouteOption {
  rank: number;
  is_primary: boolean;
  distance_m: number;
  duration_s: number;
  geometry: [number, number][]; // [lon, lat][]
}

export interface DirectionsResponse {
  origin: ResolvedPoint;
  destination: ResolvedPoint;
  criterion: "time" | "distance";
  routes: RouteOption[];
}

export const directionsApi = {
  get: (payload: DirectionsRequestPayload) => api.post<DirectionsResponse>("/directions", payload),
};
