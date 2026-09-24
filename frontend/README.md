# SIH26137 Frontend — Adaptive Traffic Intelligence

Premium enterprise frontend for the Quantum-Inspired Intelligent Traffic Route Optimization
Platform. Vite + React 18 + TypeScript (strict), Tailwind with a custom "Adaptive Traffic
Intelligence" design system, TanStack Query for server state, Zustand for client state,
MapLibre GL for the command-center map, React Three Fiber for the QPSO swarm visualization,
Recharts for convergence/benchmark charts, Framer Motion for transitions.

**Dependencies**: `package-lock.json` is committed, so `npm ci` (used by `Dockerfile`) gives a
reproducible install; every `.ts`/`.tsx` file is also verified clean with `tsc --noEmit`
against the project's `tsconfig.json` (see the root fix list for the sync-with-migration
history of that verification). Run `npm install && npm run dev` for local development, or
`docker compose up --build` from `../backend` to run frontend + backend + DB together.

## What's implemented

- **Design system** (`tailwind.config.ts`, `src/styles/globals.css`): deep graphite base,
  restrained single accent (`signal`), semantic traffic-state palette (`normal → critical`)
  used consistently everywhere congestion appears, fine background grid, thin borders —
  deliberately not a default shadcn/Tailwind template.
- **Typed API client layer** (`src/api/*`) matching the backend's actual `/api/v1` contract
  one-for-one (see `src/types/api.ts`) — no invented fields. Centralized fetch wrapper with
  the standard error envelope, Idempotency-Key passthrough, request cancellation via
  `AbortSignal`. No auth token handling -- see the "No login" bullet below.
- **No login in this build**: there is no login page, JWT decode, or `ProtectedRoute` guard.
  The router (`src/router.tsx`) goes straight to `AppShell` and its pages; the backend
  treats every request as a single hardcoded organization/principal (see the backend
  README). Add auth back by reintroducing a login route and a route guard if/when the
  backend's login flow returns.
- **App shell**: integrated (non-generic) sidebar with section grouping and an active-route
  rail indicator, top bar with the Org→Project→Network→Traffic **context selector**,
  Framer-Motion page transitions.
- **Optimization Studio** (`OptimizationPage`): algorithm selector (QPSO/PSO/GA/ACO/
  Dijkstra/A*), objective-weight sliders with named presets that fall back to "Custom" the
  moment you touch a slider, animated feasibility pre-check sequence with an explain-the-
  failure pattern (what/why/affected/action, not just a red X), live telemetry strip, and a
  convergence chart.
- **QPSOSwarmVisualization** — the signature 3D piece: an R3F instanced-mesh particle swarm
  whose spread is *actually driven* by the live convergence ratio from `useOptimizationJob`,
  not decorative. Has a static, still-informative fallback when `prefers-reduced-motion` is set.
- **`useOptimizationJob` hook**: WebSocket-first → SSE → polling fallback chain, with a
  1.5s open-timeout so the user is never left stuck if a socket path doesn't exist yet.
  Today's backend only implements the polling endpoint, so the polling path is what actually
  runs — the WS/SSE attempts fail fast and fall through cleanly, exactly as designed.
- **NetworkMap** (MapLibre): dark custom style, congestion-colored road segments, animated
  dashed selected-route overlay, customer clustering, depot markers, layer toggle buttons
  wired to Zustand `mapLayers` state.
- **Algorithm comparison table**: highlights the best value per metric column rather than
  crowning one universal winner, per the "highlight trade-offs" requirement.
- Fleet, Customers, Traffic Lab, Network Explorer, Benchmarks, Experiments, History,
  Administration pages — functional, typed, using real empty/loading/error states
  (`EmptyState`, `ErrorState`, `TableSkeleton`, `ChartSkeleton`, `MapSkeleton`).
- Accessibility basics: `:focus-visible` ring, `aria-label`/`role` on the map and traffic
  badges, semantic status text alongside every color-coded traffic state, global
  `prefers-reduced-motion` CSS kill-switch plus a `useReducedMotion()` hook for JS-driven
  animation (swarm viz, animated numbers).

## What's scaffolded / next steps

Given the scope of the spec (40 sections), these are intentionally left as clear extension
points rather than built out in full:
- **3D Network Globe** (landing) and **3D Fleet View** — the QPSO swarm viz proves out the
  R3F pattern; the globe/fleet views would reuse the same `Canvas`/instancedMesh approach.
- **Route legs on the map** — `NetworkMap` renders a straight selected-route line between
  stop coordinates today; wiring in the backend's actual `route_legs` geometry (once that
  persistence lands — see backend README) is a drop-in replacement for the coordinate array.
- **CSV/GeoJSON export dialog**, **bottom-sheet mobile layout** for panels, **virtualized
  tables** for very large customer/vehicle lists, **Radix dropdowns** for the context
  selector (currently a styled trigger button — swap in `@radix-ui/react-dropdown-menu`).
- Most data pages (`FleetPage`, `TrafficPage`, `BenchmarksPage`, etc.) call the real typed
  API client where a project is selected, but a few (`TrafficPage`, `BenchmarksPage`,
  `NetworkPage`, `HistoryPage`, `AdminPage`) currently render illustrative mock data inline
  so every screen is visually complete without a live backend — swapping in `useQuery` +
  the existing `src/api/*` functions is the remaining step, following the exact pattern
  already used in `FleetPage`/`CustomersPage`/`RoutesPage`.

## Running locally

```bash
npm install
cp .env.example .env
npm run dev
# Vite proxies /api -> http://localhost:8000 (see vite.config.ts) -- point this
# at the SIH26137 backend from the previous deliverable.
```
