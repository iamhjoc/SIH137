import { api } from "./client";
import type { GraphVersion, Project } from "@/types/api";

export const projectsApi = {
  list: () => api.get<Project[]>("/projects"),
  get: (id: string) => api.get<Project>(`/projects/${id}`),
  create: (name: string, timezone = "UTC") => api.post<Project>("/projects", { name, timezone }),
  update: (id: string, fields: Partial<Pick<Project, "name" | "status" | "timezone">>) =>
    api.patch<Project>(`/projects/${id}`, fields),
  remove: (id: string) => api.del<void>(`/projects/${id}`),
  graphs: (id: string) => api.get<GraphVersion[]>(`/projects/${id}/graphs`),
};
