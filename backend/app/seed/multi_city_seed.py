"""
Seeds one project per city, using REAL OSM road graphs and
POI-weighted synthetic customers, for the requested rollout:
all major Punjab cities + Panchkula + Chandigarh + Delhi.

Run with:
    python -m app.seed.multi_city_seed
    python -m app.seed.multi_city_seed --cities "Chandigarh, India" "Panchkula, Haryana, India"

Requires:
  - Outbound network access to Overpass (graph + POI import) -- see
    OSM_OVERPASS_URL in .env.example if you're using a mirror.
  - An organization to attach projects to (pass --org-slug, defaults to
    the org created by app/seed/dummy_data.py).

Delhi is deliberately scoped to a bounding box (not the full NCT) to
keep the graph demo-scale -- see the note in app/graph/loader.py about
full-metro pulls being tens of thousands of nodes. Adjust DELHI_BBOX
below if you want a different zone.
"""
import argparse
import asyncio

from sqlalchemy import select

from app.db.models.organization import Organization
from app.db.session import AsyncSessionLocal
from app.seed.poi_customer_generator import (
    fetch_poi_points,
    generate_poi_weighted_customers,
)
from app.services import graph_service, project_service, traffic_service
from app.services.graph_service import create_osm_graph_version

SEED = 20260909

# Major Punjab cities -- adjust this list to taste; OSMnx resolves any
# string Nominatim can geocode, so district/tehsil names also work.
PUNJAB_CITIES = [
    "Amritsar, Punjab, India",
    "Ludhiana, Punjab, India",
    "Jalandhar, Punjab, India",
    "Patiala, Punjab, India",
    "Bathinda, Punjab, India",
    "Mohali, Punjab, India",
    "Hoshiarpur, Punjab, India",
    "Pathankot, Punjab, India",
    "Moga, Punjab, India",
    "Firozpur, Punjab, India",
    "Kapurthala, Punjab, India",
    "Sangrur, Punjab, India",
    "Barnala, Punjab, India",
    "Faridkot, Punjab, India",
    "Fatehgarh Sahib, Punjab, India",
    "Gurdaspur, Punjab, India",
    "Sri Muktsar Sahib, Punjab, India",
    "Rupnagar, Punjab, India",
    "Nawanshahr, Punjab, India",
    "Tarn Taran, Punjab, India",
    "Mansa, Punjab, India",
    "Fazilka, Punjab, India",
    "Malerkotla, Punjab, India",
]

EXTRA_CITIES = [
    "Panchkula, Haryana, India",
    "Chandigarh, India",
]

# Delhi via bbox (a manageable central zone) instead of place_name, to
# avoid pulling the entire NCT's road network for a demo.
DELHI_BBOX = {"north": 28.70, "south": 28.55, "east": 77.28, "west": 77.12}


async def seed_city(db, organization_id, city_label: str, place_name: str | None = None, bbox: dict | None = None):
    project = await project_service.create_project(db, organization_id, f"{city_label} Delivery Network", timezone="Asia/Kolkata")

    graph_version = await create_osm_graph_version(db, project.id, place_name=place_name, bbox=bbox)

    # POI-weighted synthetic customers -- real geography, synthetic demand.
    poi_source = place_name or city_label
    poi_points = fetch_poi_points(poi_source, limit=300)
    customer_coords = generate_poi_weighted_customers(poi_points, count=60, seed=SEED)

    from app.db.models.customer import Customer
    from app.graph.mapper import map_coordinate_to_graph_node
    g = graph_service.load_networkx_graph(graph_version)

    for i, (lat, lon) in enumerate(customer_coords):
        try:
            node_id = map_coordinate_to_graph_node(g, lat, lon)
        except Exception:
            continue  # skip points that fall outside the imported graph's coverage
        from geoalchemy2.shape import from_shape
        from shapely.geometry import Point
        db.add(Customer(
            project_id=project.id, external_ref=f"{city_label[:3].upper()}-{i+1:04d}",
            name=f"Customer {i+1}", location=from_shape(Point(lon, lat), srid=4326),
            graph_node_id=node_id, demand_units=int((i % 12) + 1), service_seconds=300, status="active",
        ))

    traffic_scenario = await traffic_service.create_simulated_traffic_scenario(
        db, project.id, graph_version.id, f"{city_label} Simulated Traffic", SEED
    )
    # To use real live traffic instead, once TRAFFIC_PROVIDER/TRAFFIC_API_KEY
    # are set in .env:
    #   traffic_scenario = await traffic_service.create_live_traffic_scenario(
    #       db, project.id, graph_version.id, f"{city_label} Live Traffic")

    await db.flush()
    print(f"  {city_label}: project={project.id} graph_v{graph_version.version_no} "
          f"({graph_version.node_count} nodes) traffic={traffic_scenario.name}")
    return project


async def main(cities: list[str] | None, org_slug: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Organization).where(Organization.slug == org_slug))
        org = result.scalar_one_or_none()
        if org is None:
            raise SystemExit(f"Organization '{org_slug}' not found -- run app.seed.dummy_data first, or pass --org-slug.")

        targets = cities or (PUNJAB_CITIES + EXTRA_CITIES)
        print(f"Seeding {len(targets)} cities + Delhi into organization '{org_slug}'...")

        for city in targets:
            label = city.split(",")[0]
            await seed_city(db, org.id, label, place_name=city)

        await seed_city(db, org.id, "Delhi", bbox=DELHI_BBOX)
        await db.commit()

    print("Multi-city seed complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cities", nargs="*", default=None, help="Override the default city list.")
    parser.add_argument("--org-slug", default="ludhiana-logistics")
    args = parser.parse_args()
    asyncio.run(main(args.cities, args.org_slug))
