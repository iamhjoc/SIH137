# SIH26137 — Quantum-Inspired Intelligent Traffic Route Optimization Platform

Backend implementation per the provided PRD, Technology & Architecture spec, and Backend
Schema & Data Model. Modular monorepo: FastAPI (`/api/v1`) + PostgreSQL/PostGIS +
Redis + Celery worker running the QPSO optimization engine asynchronously.

## What's implemented

- **All 18 core tables** as SQLAlchemy models (`app/db/models/`) with UUID PKs,
  `timestamptz` columns, PostGIS geometry columns, and the required unique/FK constraints
  (organization isolation, project ownership, capacity checks are enforced in the repair/
  validation layer, depot start/end rules).
- **Real QPSO engine** (`app/optimization/`): random-key encoding, greedy decoder,
  capacity/visit-once/depot/connectivity repair, configurable weighted fitness function,
  beta-interpolated quantum PSO update, multi-condition termination, full iteration history.
- **Baseline algorithms** (`app/benchmarks/algorithms.py`): Dijkstra nearest-neighbor,
  A* nearest-neighbor, classical PSO, GA, ACO — all implementing the same
  `RoutingAlgorithm` interface as QPSO so the benchmark runner is algorithm-agnostic.
  None of these fabricate numbers; every run actually executes the algorithm.
- **Async worker flow**: `POST /optimization-jobs` validates + persists + queues a Celery
  task and returns immediately; `app/workers/optimization_worker.py` performs the
  `queued -> running -> succeeded/failed` state machine and writes progress to Redis.
- **Pre-optimization feasibility check** (`app/optimization/validation.py`) — infeasible
  requests are rejected before the (expensive) job is ever queued.
- **No login for this build**: every request is treated as a single hardcoded principal
  (`DEFAULT_ORGANIZATION_ID`, role `ADMIN`) via `get_current_principal` in
  `app/core/dependencies.py`. `require_role(...)` dependencies and organization-scoped
  multi-tenancy checks are still enforced at the service layer on every query; there is
  just no JWT/login flow in front of them in this build.
- **Standard error envelope**, request-id middleware, audit logging with secret-key scrubbing.
- **Deterministic synthetic 10x10 grid graph + simulated traffic generator**, both seeded
  (`seed=20260909` by default) for reproducibility.
- **Comprehensive seed script** (`python -m app.seed.dummy_data`): 2 orgs, 5 role-based
  users, 1 project, 2 depots, 60 customers, 8 vehicles, a graph version, a traffic
  scenario, and one queued sample optimization job — all internally consistent.
- Docker Compose (Postgres+PostGIS, Redis, API, Celery worker), Alembic wiring, `.env.example`.
- **Real OSM road graphs** via OSMnx (`POST /graphs/import-osm`, place name or bbox).
- **Pluggable geocoding** (Nominatim/Google/Mappls) wired into customer/depot creation and a
  new bulk CSV/JSON-style import endpoint (`POST /projects/{id}/customers/import`) with
  per-row validation so one bad address doesn't fail the whole batch.
- **Pluggable live traffic** (TomTom/HERE/Mappls) via `POST /traffic/scenarios/live`.
- **S3-compatible object storage** for graph artifacts (swap via `OBJECT_STORAGE_BACKEND`).
- **Multi-city seed script** (`app/seed/multi_city_seed.py`) with real OSM graphs and
  POI-weighted synthetic customers, pre-configured for Punjab's major cities + Panchkula +
  Chandigarh + Delhi.
- Production deployment: `docker-compose.prod.yml` + Caddy reverse proxy (automatic TLS),
  env-driven CORS allowlist.

## Switching from synthetic/simulated data to real data

All of this is `.env`-driven -- **you only need to edit `.env`, not source code**, to switch
providers. Copy `.env.example` to `.env` and fill in the section marked "PUT YOUR REAL API
KEYS BELOW":

| # | What | Where the key goes | Where it's used |
|---|------|--------------------|-------------------|
| 1 | Road graph (OSM) | `OSM_OVERPASS_URL` (optional — public Overpass needs no key) | `app/graph/loader.py`, new `POST /api/v1/graphs/import-osm` |
| 2 | Geocoding | `GEOCODING_PROVIDER` + `GEOCODING_API_KEY` | `app/geocoding/adapters.py`, used by customer/depot creation and bulk import |
| 3 | Traffic | `TRAFFIC_PROVIDER` + `TRAFFIC_API_KEY` | `app/traffic/adapters.py`, new `POST /api/v1/traffic/scenarios/live` |

Supported providers out of the box: geocoding = `nominatim` (free) / `google` / `mappls`;
traffic = `simulated` (free, deterministic) / `tomtom` / `here` / `mappls`. If your chosen
provider isn't one of these, add a new adapter class implementing the same interface — the
factory functions (`get_geocoding_adapter()`, `get_traffic_adapter()`) are the only things
that need a new branch.

**Multi-city rollout**: `python -m app.seed.multi_city_seed` seeds one project per city —
pre-configured for all major Punjab cities plus Panchkula, Chandigarh, and Delhi (Delhi is
bbox-scoped to a manageable zone rather than the full NCT — see the comment in that file).
Each project gets a real OSM road graph and POI-weighted synthetic customers (real
geography, synthetic demand — see the "customer data" discussion: there's no public API for
actual delivery demand, so this stays the honest approach for a demo). Run
`python -m app.seed.dummy_data` first to create the organization it attaches to, or pass
`--org-slug`.

**Object storage**: switch `OBJECT_STORAGE_BACKEND=s3` in `.env` before deploying publicly —
the filesystem backend doesn't survive redeploys and isn't shared across multiple worker
instances. Fill in `S3_BUCKET`/`S3_ACCESS_KEY`/`S3_SECRET_KEY` (any S3-compatible provider
works — AWS S3, Cloudflare R2, Backblaze B2, DigitalOcean Spaces).

## Deploying publicly

1. Provision a host (a single small VPS is enough for a demo — DigitalOcean, AWS Lightsail,
   Hetzner, etc. — or use a managed platform like Railway/Render if you'd rather not manage
   Docker yourself).
2. Point a domain's A record at the host, and set that domain in `Caddyfile`.
3. On the host:
   ```bash
   git clone <your-repo> && cd backend
   cp .env.example .env   # fill in DB/Redis passwords, your API keys, S3 creds
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
   docker compose exec api alembic upgrade head
   docker compose exec api python -m app.seed.dummy_data        # or multi_city_seed
   ```
   Caddy automatically obtains and renews a Let's Encrypt TLS certificate for the domain in
   `Caddyfile` — no manual certbot steps.
4. Set `CORS_ALLOWED_ORIGINS` in `.env` to your deployed frontend's exact URL(s) before going
   live — the dev default of `*` is not safe for production and disables credentialed CORS
   automatically (see `app/main.py`).

## What's scaffolded / next steps

Given the scope of the spec (50 sections), the following are stubbed with clear
extension points rather than fully built out — they follow the same patterns as the
completed pieces:
- **Cursor-based pagination beyond `id >`**, **SSE/WebSocket progress streaming**, and
  **OpenTelemetry/Prometheus wiring**. (Bulk customer import and S3 object storage are now
  implemented — see "Switching from synthetic/simulated data to real data" below.)
- `route_legs` persistence and full route geometry generation (`app/graph/geometry.py`
  has the LineString builder; wiring it into `optimization_service.persist_route_result`
  is the remaining step).
- Additional endpoint coverage (PATCH/DELETE for customers/vehicles/depots, list filters).

## Running locally

```bash
cp .env.example .env
docker compose up --build
# in another shell, once containers are healthy:
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed.dummy_data
```

A migration already exists in `migrations/versions/`, so just run `alembic upgrade head` —
do **not** run `alembic revision --autogenerate -m "init"` first; that command requires the
database to already be at head and will fail with "Target database is not up to date" on a
fresh database.

API docs: http://localhost:8000/docs

`docker compose up --build` also builds and serves the frontend (see `../frontend`) at
http://localhost:8080 — its nginx container proxies `/api/` straight to the `api` service, so
no `VITE_API_BASE` build-arg is needed for local use.

There is no login in this build — every request is served under a single hardcoded
organization/principal (see `app/core/dependencies.py`). The `admin@example.com` /
`manager@example.com` / etc. seeded users exist as data rows only; there is no
password-based sign-in.

## Tests

```bash
pytest tests/unit          # QPSO engine, decoder, repair, fitness — no DB required
```
