/**
 * Centralized, typed fetch client. Every API call in the app goes through
 * this module -- components never call fetch() directly.
 *
 * Responsibilities:
 *  - Base URL / API versioning (/api/v1)
 *  - Standard error envelope parsing (ApiError)
 *  - Request cancellation via AbortSignal
 *  - Idempotency-Key passthrough for expensive mutations
 *
 * Note: there is no authentication in this app -- no tokens are attached
 * to requests and none are expected back.
 */
import type { ApiErrorEnvelope } from "@/types/api";

// In dev, Vite's proxy (vite.config.ts) forwards /api -> localhost:8000, so
// the relative default works with no env var needed. In production, set
// VITE_API_BASE in your deployment platform's env vars (e.g. Vercel/Netlify
// project settings, or a .env.production file) to your deployed backend's
// public URL, e.g. https://api.yourdomain.com/api/v1
const API_BASE = import.meta.env.VITE_API_BASE || "/api/v1";

export class ApiError extends Error {
  code: string;
  details: Record<string, unknown>;
  requestId: string;
  status: number;

  constructor(envelope: ApiErrorEnvelope, status: number) {
    super(envelope.message);
    this.code = envelope.code;
    this.details = envelope.details;
    this.requestId = envelope.request_id;
    this.status = status;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
  idempotencyKey?: string;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, signal, idempotencyKey } = options;

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  if (!res.ok) {
    let envelope: ApiErrorEnvelope;
    try {
      envelope = await res.json();
    } catch {
      envelope = { code: "UNKNOWN_ERROR", message: res.statusText, details: {}, request_id: "" };
    }
    throw new ApiError(envelope, res.status);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal) => apiRequest<T>(path, { method: "GET", signal }),
  post: <T>(path: string, body?: unknown, opts?: Partial<RequestOptions>) =>
    apiRequest<T>(path, { method: "POST", body, ...opts }),
  patch: <T>(path: string, body?: unknown) => apiRequest<T>(path, { method: "PATCH", body }),
  del: <T>(path: string) => apiRequest<T>(path, { method: "DELETE" }),
};
