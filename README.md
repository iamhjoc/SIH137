# SIH26137 -- Quantum-Inspired Traffic Routing Platform

A full-stack vehicle routing optimizer: a custom QPSO (Quantum Particle
Swarm Optimization) algorithm benchmarked against classical baselines
(Dijkstra, A*, GA, ACO, PSO), plus a point-to-point Directions feature
that works for any address in India. FastAPI + PostgreSQL/PostGIS + Redis
+ Celery on the backend, React + Vite + TypeScript + MapLibre on the
frontend.

This README is written so that **following it top to bottom, in order,
gets you a fully working local instance** -- the ordering matters (e.g.
migrations before seeding, seeding before first login) and skipping a
step is the most common cause of "it's running but nothing works."

---

## Option A: Everything via Docker (recommended, least error-prone)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/)
installed and running.

```bash
cd backend
cp .env.example .env
```

Open `.env` and change one line for local development:
```
OBJECT_STORAGE_BACKEND=filesystem
```
(The default, `s3`, needs real AWS credentials -- fine for a real
deployment, not needed for running this locally.)

Then:
```bash
docker compose up --build
```

This starts **five** containers: `postgres`, `redis`, `api` (port 8000),
`worker` (Celery -- **required**, see "Why routes never finish" below),
and `frontend` (nginx, port 8080, already configured to proxy `/api` to
the `api` container -- no extra setup needed).

Wait until all containers report healthy (`docker compose ps`), then in
a **new terminal**, run migrations and seed data:
```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed.dummy_data
```

Open **http://localhost:8080** -- you should see real seeded data (a
project, depots, vehicles, customers) immediately, not empty states.

---

## Option B: Backend in Docker, frontend via `npm run dev` (for active frontend development)

Same first steps as Option A, but only start the backend services:
```bash
cd backend
  cp .env.example .env
# edit .env: OBJECT_STORAGE_BACKEND=filesystem
docker compose up --build postgres redis api worker
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed.dummy_data
```

Confirm the backend is actually reachable before touching the frontend:
open **http://localhost:8000/docs** in a browser. If that doesn't load,
stop here and fix it first -- nothing on the frontend will work otherwise.

Then, in another terminal:
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173**. Vite's dev-server proxy (`vite.config.ts`)
forwards `/api` to `http://localhost:8000` automatically -- no `.env`
needed for local dev.

---

## Seed data reference

Three seed scripts, different levels of realism (run from inside the
`api` container or a local venv with the backend's dependencies installed):

| Script | What you get |
|---|---|
| `python -m app.seed.dummy_data` | Fastest. One project ("Ludhiana Delivery Optimization"), a **synthetic 10x10 grid** road network (not real roads), 2 depots, 8 vehicles, 60 customers, 1 traffic scenario, 1 pre-queued optimization job. |
| `python -m app.seed.multi_city_seed` | Real OSM-imported road networks for Punjab cities + Chandigarh/Panchkust/Delhi, with POI-weighted synthetic customer demand. Takes longer (live OSM download). |
| `python -m app.seed.demo_scenario` | A canned scenario -- read the file for specifics. |

Run at most one of these on a fresh database; running more than one adds
more projects rather than conflicting.

---

## Verifying everything actually works

Don't skip this -- it catches 90% of "it's running but nothing works" reports.

1. **Backend reachable**: `http://localhost:8000/docs` loads the FastAPI docs UI.
2. **Frontend reachable**: `http://localhost:8080` (Docker) or `http://localhost:5173` (`npm run dev`) loads the app.
3. **Data flowing**: the Overview page shows real numbers (not all zeros/empty), and the project selector in the top bar has at least one project.
4. **Celery worker running**: `docker compose ps` shows `worker` as `Up` (Option A), or you separately started `celery -A app.workers.celery_app worker --loglevel=INFO` (Option B, manual backend). **If this isn't running, every optimization job and benchmark will sit at `queued` forever and never produce a result** -- this was the single most common issue while building this out.
5. **End-to-end smoke test**: Optimization Studio -> Run Optimization -> wait for it to reach "succeeded" -> click "View Optimized Routes" -> you should see a real path drawn on the map.

---

## Environment variables

`backend/.env.example` is thoroughly commented -- read it before asking
"where do I get an API key." Short version:
- **Geocoding** (`GEOCODING_PROVIDER=nominatim`) needs no key by default.
- **Traffic** (`TRAFFIC_PROVIDER=simulated`) needs no key by default --
  switch to `tomtom`/`here`/`mappls` + an API key only if you want live
  provider traffic instead of synthetic congestion.
- **Map tiles** (`frontend/.env.example` -> `VITE_MAP_TILE_URL`): left
  blank, the app uses OSM's free demo tile server, which is
  explicitly **not meant for real usage and rate-limits under load**
  (this looks like "the map is unstable/tiles flicker" if you hit it).
  Put a real tile provider's URL here (MapTiler, Stadia Maps -- both have
  free tiers) before relying on this for anything beyond a quick local check.

---

## What's real vs. what's a known gap, right now

Every number/list on every page below is now backed by a real API call
-- no `MOCK_*` constants remain anywhere in the frontend:

| Area | Status |
|---|---|
| Projects, Depots, Vehicles, Customers (list + create) | Real |
| Optimization Studio (run, live progress, feasibility pre-check, map) | Real |
| Routes (view a completed job's path on the map) | Real |
| Overview, Operations (KPIs + map) | Real |
| Traffic Lab (scenarios, congestion stats, create scenario) | Real |
| Benchmarks (run, per-algorithm comparison table) | Real |
| Decision History (past optimization runs) | Real |
| Directions (source -> destination, works for any address in India) | Real |
| Experiments | Redirects to Benchmarks (same backend concept, was a dead button before) |
| Administration | Intentionally **not implemented** -- see below |

**Administration is the one honest gap left.** This app has no
authentication or user-management system: every request runs as a
single hardcoded `ADMIN` principal (`backend/app/core/dependencies.py`).
There's no backend endpoint for users/roles to make this page real
without first building an actual auth system, which is out of scope of
a "replace fake data with real data" pass. The page now shows a plain
"not built yet" message instead of a fabricated user table.

Two smaller, by-design limitations, documented in code where they live:
- **Directions'** per-request road-network cache is in-process memory
  only (empty on restart, not shared across multiple worker processes) --
  see the docstring in `backend/app/services/directions_service.py`.
- The map (`NetworkMap.tsx`) uses free OSM tiles by default -- see
  "Environment variables" above.

---

## Troubleshooting

- **Buttons don't do anything / pages are empty**: see "Verifying
  everything actually works" above, in order. 95% of the time it's the
  Celery worker not running, or the backend not reachable at all.
- **"Run Optimization" button is disabled**: the Feasibility Pre-Check
  panel on the left will tell you exactly which requirement isn't met
  yet (no graph, no customers, no vehicles, insufficient vehicle
  capacity for total demand, or no depot) -- it's real validation now,
  not decoration.
- **A new project you create shows nothing on the map / optimization
  silently does nothing**: a brand-new project has no graph version yet
  and there's currently no "Import Graph" UI (the backend endpoint,
  `POST /graphs/import-osm`, exists; nothing calls it from the frontend
  yet). Use one of the seed scripts above to get a project with a graph
  already attached, or use the Directions page, which doesn't need a
  project's graph at all.
- **Map tiles flicker or fail to load**: you're hitting the free OSM
  demo tile server's rate limit -- set `VITE_MAP_TILE_URL` to a real
  provider (see "Environment variables").
