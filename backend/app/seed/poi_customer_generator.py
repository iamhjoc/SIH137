"""
Generates synthetic customer points weighted toward real points-of-interest
(shops, restaurants, residential buildings) pulled from OpenStreetMap/
Overpass for a given place, instead of scattering customers uniformly at
random. Business/demand numbers stay synthetic (see conversation notes --
there is no public API for "who needs a delivery today"), but *where*
those synthetic customers sit is grounded in real geography, which is
what makes a multi-city demo look credible instead of obviously fake.

Requires network access to Overpass at runtime (same dependency as the
OSM graph import in app/graph/loader.py).
"""
from __future__ import annotations

import numpy as np


def fetch_poi_points(place_name: str, tags: dict[str, str | bool] | None = None, limit: int = 500) -> list[tuple[float, float]]:
    """
    Returns up to `limit` (lat, lon) points for commercial/residential POIs
    in `place_name`. Default tag set favors delivery-relevant locations:
    shops, restaurants, and residential buildings.
    """
    import osmnx as ox

    tags = tags or {"shop": True, "amenity": ["restaurant", "cafe", "pharmacy", "supermarket"], "building": "residential"}
    gdf = ox.features_from_place(place_name, tags=tags)

    points: list[tuple[float, float]] = []
    for geom in gdf.geometry:
        centroid = geom.centroid
        points.append((centroid.y, centroid.x))
        if len(points) >= limit:
            break

    return points


def generate_poi_weighted_customers(
    poi_points: list[tuple[float, float]], count: int, seed: int, jitter_degrees: float = 0.0008,
) -> list[tuple[float, float]]:
    """
    Samples `count` customer locations by picking a real POI point (with
    replacement if count > len(poi_points)) and adding small jitter so
    customers don't all land exactly on the POI centroid. Deterministic
    given the same seed.
    """
    if not poi_points:
        raise ValueError("No POI points available -- fetch_poi_points returned an empty list for this place.")

    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(poi_points), size=count)

    customers = []
    for idx in indices:
        lat, lon = poi_points[idx]
        jitter_lat = rng.uniform(-jitter_degrees, jitter_degrees)
        jitter_lon = rng.uniform(-jitter_degrees, jitter_degrees)
        customers.append((lat + jitter_lat, lon + jitter_lon))

    return customers
