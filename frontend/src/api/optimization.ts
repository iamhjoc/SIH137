import { api } from "./client";
import type {
  OptimizationJob, OptimizationJobCreateRequest, OptimizationProgress, OptimizationResultResponse,
} from "@/types/api";

export const optimizationApi = {
  create: (payload: OptimizationJobCreateRequest, idempotencyKey: string) =>
    api.post<OptimizationJob>("/optimization-jobs", payload, { idempotencyKey }),
  list: (projectId: string, limit = 50) =>
    api.get<OptimizationJob[]>(`/optimization-jobs?project_id=${projectId}&limit=${limit}`),
  get: (id: string) => api.get<OptimizationJob>(`/optimization-jobs/${id}`),
  progress: (id: string, signal?: AbortSignal) =>
    api.get<OptimizationProgress>(`/optimization-jobs/${id}/progress`, signal),
  routes: (id: string) => api.get<OptimizationResultResponse>(`/optimization-jobs/${id}/routes`),
  cancel: (id: string) => api.post<OptimizationJob>(`/optimization-jobs/${id}/cancel`),
  rerun: (id: string) => api.post<OptimizationJob>(`/optimization-jobs/${id}/rerun`),
};
