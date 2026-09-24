"""
Comprehensive, internally-consistent dummy data generator.

Run with:
    python -m app.seed.dummy_data

Creates 2 organizations, 5 users (one per role) in the primary org,
a "Ludhiana Delivery Optimization" project with depots, 20-100
customers, 5-10 vehicles, a synthetic graph, a simulated traffic
scenario, and one sample optimization job/result -- all wired with
valid, project-scoped foreign keys (section 41).

Everything here is generator code, kept out of app/services/*, so
production business logic never depends on dummy data (section 42).
"""
import asyncio

import numpy as np
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.dependencies import DEFAULT_ORGANIZATION_ID
from app.core.security import hash_password
from app.db.models.customer import Customer
from app.db.models.depot import Depot
from app.db.models.organization import Organization
from app.db.models.user import User
from app.db.models.vehicle import Vehicle
from app.db.session import AsyncSessionLocal
from app.services import project_service
from app.services.graph_service import create_synthetic_graph_version
from app.services.optimization_service import create_optimization_job
from app.services.traffic_service import create_simulated_traffic_scenario

SEED = 20260909
DEV_PASSWORD = "DevPassword123!"  # documented dummy password -- development only

ROLE_EMAILS = [
    ("admin@example.com", "ADMIN"),
    ("manager@example.com", "MANAGER"),
    ("dispatcher@example.com", "DISPATCHER"),
    ("analyst@example.com", "ANALYST"),
    ("viewer@example.com", "VIEWER"),
]


async def seed():
    rng = np.random.default_rng(SEED)

    async with AsyncSessionLocal() as db:
        # The API scopes every request to DEFAULT_ORGANIZATION_ID (see
        # app/core/dependencies.py -- there is no login, so this is the only
        # organization the app will ever query as). The primary seeded org
        # MUST use that same fixed id, or the seeded project/customers/etc.
        # are invisible to every list endpoint.
        await db.execute(
            pg_insert(Organization)
            .values(
                id=DEFAULT_ORGANIZATION_ID,
                name="Ludhiana Logistics Pvt Ltd",
                slug="ludhiana-logistics",
                status="active",
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await db.flush()
        org1 = await db.get(Organization, DEFAULT_ORGANIZATION_ID)

        org2 = Organization(name="Punjab Regional Freight", slug="punjab-regional-freight", status="active")
        db.add(org2)
        await db.flush()

        for email, role in ROLE_EMAILS:
            db.add(User(
                organization_id=org1.id, email=email, full_name=email.split("@")[0].title(),
                hashed_password=hash_password(DEV_PASSWORD), role=role, is_active=True,
            ))
        db.add(User(
            organization_id=org2.id, email="admin@punjabfreight.example.com", full_name="Org2 Admin",
            hashed_password=hash_password(DEV_PASSWORD), role="ADMIN", is_active=True,
        ))
        await db.flush()

        project = await project_service.create_project(db, org1.id, "Ludhiana Delivery Optimization", timezone="Asia/Kolkata")

        base_lat, base_lon = 30.9010, 75.8573
        depot_a = Depot(project_id=project.id, name="Central Depot",
                         location=from_shape(Point(base_lon, base_lat), srid=4326), status="active")
        depot_b = Depot(project_id=project.id, name="North Depot",
                         location=from_shape(Point(base_lon + 0.05, base_lat + 0.05), srid=4326), status="active")
        db.add_all([depot_a, depot_b])
        await db.flush()

        graph_version = await create_synthetic_graph_version(db, project.id, SEED, rows=10, cols=10)

        # Map depots to graph nodes deterministically (corners of the grid).
        depot_a.graph_node_id = "n_0_0"
        depot_b.graph_node_id = "n_5_5"
        await db.flush()

        num_customers = 60
        customers = []
        for i in range(num_customers):
            r, c = int(rng.integers(0, 10)), int(rng.integers(0, 10))
            lat = base_lat + r * 0.01 + rng.uniform(-0.002, 0.002)
            lon = base_lon + c * 0.01 + rng.uniform(-0.002, 0.002)
            customer = Customer(
                project_id=project.id, external_ref=f"CUST-{i+1:04d}", name=f"Customer {i+1}",
                location=from_shape(Point(lon, lat), srid=4326),
                graph_node_id=f"n_{r}_{c}",
                demand_units=int(rng.integers(1, 15)),
                service_seconds=int(rng.integers(180, 600)),
                priority=int(rng.integers(1, 4)),
                status="active",
            )
            customers.append(customer)
        db.add_all(customers)
        await db.flush()

        num_vehicles = 8
        vehicles = []
        for i in range(num_vehicles):
            vehicle = Vehicle(
                project_id=project.id, code=f"VEH-{i+1:03d}",
                capacity_units=int(rng.choice([50, 80, 100, 150])),
                fixed_cost=float(rng.uniform(500, 1500)),
                cost_per_km=float(rng.uniform(8, 20)),
                max_route_seconds=28800,
                start_depot_id=depot_a.id if i % 2 == 0 else depot_b.id,
                end_depot_id=depot_a.id if i % 2 == 0 else depot_b.id,
                status="active",
            )
            vehicles.append(vehicle)
        db.add_all(vehicles)
        await db.flush()

        traffic_scenario = await create_simulated_traffic_scenario(
            db, project.id, graph_version.id, "Weekday Simulated Traffic", SEED
        )

        job = await create_optimization_job(
            db, project.id, graph_version.id, traffic_scenario.id, "qpso", SEED,
            objective_weights={"distance": 0.25, "time": 0.40, "congestion": 0.25, "late": 0.10, "vehicle": 0.0, "constraint": 1.0},
            algorithm_config={"particles": 40, "iterations": 100, "beta_start": 1.0, "beta_end": 0.5},
            constraints={"capacity": True, "visit_once": True, "return_to_depot": True},
            idempotency_key="seed-demo-job",
        )

        await db.commit()

        print("Seed complete:")
        print(f"  organizations: {org1.slug}, {org2.slug}")
        print(f"  users: {[e for e, _ in ROLE_EMAILS]} (password: {DEV_PASSWORD})")
        print(f"  project: {project.name} ({project.id})")
        print(f"  depots: {depot_a.name}, {depot_b.name}")
        print(f"  customers: {num_customers}")
        print(f"  vehicles: {num_vehicles}")
        print(f"  graph_version: v{graph_version.version_no} ({graph_version.node_count} nodes, {graph_version.edge_count} edges)")
        print(f"  traffic_scenario: {traffic_scenario.name}")
        print(f"  optimization_job (queued): {job.id}")
        print("  -> run `celery -A app.workers.celery_app worker` to process it.")


if __name__ == "__main__":
    asyncio.run(seed())
