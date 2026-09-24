/**
 * Client (UI) state: the context-aware Org -> Project -> Network -> Traffic
 * selector, plus map layer visibility and panel state. Server data itself
 * (projects, customers, jobs...) lives in TanStack Query, NOT here.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type MapLayerKey = "roads" | "traffic" | "routes" | "customers" | "depots" | "vehicles" | "graph";

interface AppState {
  currentProjectId: string | null;
  currentGraphVersionId: string | null;
  currentTrafficScenarioId: string | null;
  setContext: (fields: Partial<Pick<AppState, "currentProjectId" | "currentGraphVersionId" | "currentTrafficScenarioId">>) => void;

  selectedRouteVehicleId: string | null;
  setSelectedRoute: (vehicleId: string | null) => void;

  lastOptimizationJobId: string | null;
  setLastOptimizationJobId: (jobId: string | null) => void;

  mapLayers: Record<MapLayerKey, boolean>;
  toggleMapLayer: (key: MapLayerKey) => void;

  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      currentProjectId: null,
      currentGraphVersionId: null,
      currentTrafficScenarioId: null,
      setContext: (fields) => set((s) => ({ ...s, ...fields })),

      selectedRouteVehicleId: null,
      setSelectedRoute: (vehicleId) => set({ selectedRouteVehicleId: vehicleId }),

      lastOptimizationJobId: null,
      setLastOptimizationJobId: (jobId) => set({ lastOptimizationJobId: jobId }),

      mapLayers: {
        roads: true, traffic: true, routes: true,
        customers: true, depots: true, vehicles: false, graph: false,
      },
      toggleMapLayer: (key) =>
        set((s) => ({ mapLayers: { ...s.mapLayers, [key]: !s.mapLayers[key] } })),

      sidebarCollapsed: false,
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
    }),
    { name: "sih26137-app-context" },
  ),
);
