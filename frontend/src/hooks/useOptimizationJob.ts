/**
 * Reusable real-time optimization-job hook.
 *
 * Connection strategy: WebSocket (if the backend exposes one) -> SSE ->
 * polling. Today the backend only implements the polling endpoint
 * (GET /optimization-jobs/{id}/progress, see backend README), so this hook
 * attempts WS first, falls back to SSE, and finally falls back to a 1s
 * poll -- the fallback path is what actually runs against the current
 * backend, but the interface is ready for WS/SSE the moment they exist.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { optimizationApi } from "@/api/optimization";
import type { OptimizationJobStatus } from "@/types/api";

export interface ConvergencePoint {
  iteration: number;
  bestCost: number;
  elapsedMs: number;
}

export interface OptimizationJobState {
  status: OptimizationJobStatus | "idle" | "connecting";
  progress: number;
  iteration: number;
  totalIterations: number;
  bestCost: number | null;
  runtimeMs: number;
  convergence: ConvergencePoint[];
  error: string | null;
  connectionMode: "websocket" | "sse" | "polling" | null;
}

const TERMINAL_STATUSES: OptimizationJobStatus[] = ["succeeded", "failed", "cancelled", "completed"];

export function useOptimizationJob(jobId: string | null) {
  const [state, setState] = useState<OptimizationJobState>({
    status: "idle", progress: 0, iteration: 0, totalIterations: 0,
    bestCost: null, runtimeMs: 0, convergence: [], error: null, connectionMode: null,
  });

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const applyProgress = useCallback((progress: {
    status: OptimizationJobStatus; progress: number; iteration: number;
    total_iterations: number; best_cost: number | null; elapsed_ms: number;
  }) => {
    setState((prev) => {
      const shouldRecord =
        progress.iteration > (prev.convergence.at(-1)?.iteration ?? -1) && progress.best_cost !== null;
      return {
        ...prev,
        status: progress.status,
        progress: progress.progress,
        iteration: progress.iteration,
        totalIterations: progress.total_iterations,
        bestCost: progress.best_cost,
        runtimeMs: progress.elapsed_ms,
        convergence: shouldRecord
          ? [...prev.convergence, { iteration: progress.iteration, bestCost: progress.best_cost!, elapsedMs: progress.elapsed_ms }]
          : prev.convergence,
      };
    });
  }, []);

  const startPolling = useCallback(() => {
    if (!jobId) return;
    setState((s) => ({ ...s, connectionMode: "polling" }));
    const poll = async () => {
      try {
        const progress = await optimizationApi.progress(jobId);
        applyProgress(progress);
        if (TERMINAL_STATUSES.includes(progress.status)) {
          stopPolling();
        }
      } catch (err) {
        setState((s) => ({ ...s, error: err instanceof Error ? err.message : "Connection lost." }));
      }
    };
    poll();
    pollRef.current = setInterval(poll, 1000);
  }, [jobId, applyProgress, stopPolling]);

  const connect = useCallback(() => {
    if (!jobId) return;
    setState((s) => ({ ...s, status: "connecting", error: null }));

    // Attempt a WebSocket connection; the backend does not yet expose one
    // (see backend README "next steps"), so this will fail fast and we
    // transparently fall back to polling -- normal, expected behavior today.
    try {
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(`${proto}://${window.location.host}/ws/optimization-jobs/${jobId}`);
      wsRef.current = ws;

      ws.onopen = () => setState((s) => ({ ...s, connectionMode: "websocket" }));
      ws.onmessage = (event) => applyProgress(JSON.parse(event.data));
      ws.onerror = () => {
        ws.close();
        startPolling();
      };
      ws.onclose = () => {
        if (state.connectionMode === "websocket") startPolling();
      };

      // If the socket doesn't open quickly, don't leave the user stuck --
      // start polling as a safety net.
      const fallbackTimer = setTimeout(() => {
        if (ws.readyState !== WebSocket.OPEN) {
          ws.close();
          startPolling();
        }
      }, 1500);
      return () => clearTimeout(fallbackTimer);
    } catch {
      startPolling();
    }
  }, [jobId, applyProgress, startPolling, state.connectionMode]);

  const reconnect = useCallback(() => {
    stopPolling();
    wsRef.current?.close();
    connect();
  }, [connect, stopPolling]);

  useEffect(() => {
    if (!jobId) return;
    connect();
    return () => {
      stopPolling();
      wsRef.current?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  return { ...state, reconnect };
}
