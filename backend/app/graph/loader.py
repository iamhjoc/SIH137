"""
Synthetic + real (OSMnx) road-graph generation, and object-storage-backed
persistence (filesystem for local dev, S3 for public deployment). Hides
NetworkX/OSMnx details from callers -- services only ever see a plain
nx.DiGraph with {lat, lon} on nodes and {length_m, speed_kmh} on edges,
whether it came from the synthetic generator or a real OSM pull.
"""
from __future__ import annotations

import json
import os

import networkx as nx
import numpy as np

from app.core.config import get_settings

settings = get_settings()


def generate_synthetic_grid_graph(rows: int = 10, cols: int = 10, seed: int = 20260909) -> nx.DiGraph:
    """
    Deterministic 10x10 grid (100 nodes), directed edges both ways with
    randomized-but-seeded lengths and speed limits, mimicking a real road
    network until OSM data is supplied.
    """
    rng = np.random.default_rng(seed)
    g = nx.DiGraph()

    # Place nodes on a lat/lon grid roughly centered near Ludhiana, India.
    base_lat, base_lon = 30.9010, 75.8573
    step = 0.01

    for r in range(rows):
        for c in range(cols):
            node_id = f"n_{r}_{c}"
            lat = base_lat + r * step
            lon = base_lon + c * step
            g.add_node(node_id, lat=lat, lon=lon)

    def add_edge(u: str, v: str):
        length_m = float(rng.uniform(300, 1200))
        speed_kmh = float(rng.choice([30, 40, 50, 60]))
        g.add_edge(u, v, length_m=length_m, speed_kmh=speed_kmh)

    for r in range(rows):
        for c in range(cols):
            node_id = f"n_{r}_{c}"
            if c + 1 < cols:
                right = f"n_{r}_{c+1}"
                add_edge(node_id, right)
                add_edge(right, node_id)
            if r + 1 < rows:
                down = f"n_{r+1}_{c}"
                add_edge(node_id, down)
                add_edge(down, node_id)

    return g


def import_graph_from_place(place_name: str, network_type: str = "drive") -> nx.DiGraph:
    """
    Real road graph via OSMnx/Overpass. `place_name` is anything Nominatim
    can resolve, e.g. "Chandigarh, India", "Panchkula, Haryana, India",
    "Ludhiana, Punjab, India", "New Delhi, India".

    For large metros (Delhi), prefer `import_graph_from_bbox` with a
    deliberately small bounding box (a city-center zone, not the whole
    municipal area) -- a full-metro pull can be tens of thousands of nodes,
    which is both slow against the public Overpass API and far larger than
    the QPSO engine's particle/decode cost model is tuned for.

    Requires network access to Overpass at runtime -- this only works
    where OSM_OVERPASS_URL (if set) or the public Overpass API is
    reachable, which this development sandbox is not.
    """
    import osmnx as ox

    if settings.osm_overpass_url:
        ox.settings.overpass_endpoint = settings.osm_overpass_url

    raw = ox.graph_from_place(place_name, network_type=network_type, simplify=True)
    return _convert_osmnx_graph(raw)


def import_graph_from_bbox(north: float, south: float, east: float, west: float, network_type: str = "drive") -> nx.DiGraph:
    """Same as import_graph_from_place, but scoped to an explicit bounding
    box -- the recommended path for large cities (Delhi) where a full
    place-name pull would be excessive for a demo-scale graph."""
    import osmnx as ox

    if settings.osm_overpass_url:
        ox.settings.overpass_endpoint = settings.osm_overpass_url

    raw = ox.graph_from_bbox((north, south, east, west), network_type=network_type, simplify=True)
    return _convert_osmnx_graph(raw)


def _convert_osmnx_graph(raw) -> nx.DiGraph:
    """Convert an OSMnx MultiDiGraph into this project's plain DiGraph
    schema: node {lat, lon}, edge {length_m, speed_kmh}. Parallel edges
    (MultiDiGraph can have >1 edge between the same u,v) are collapsed to
    the shortest one, since the rest of the codebase assumes a simple
    DiGraph."""

    g = nx.DiGraph()
    for node_id, data in raw.nodes(data=True):
        g.add_node(str(node_id), lat=data["y"], lon=data["x"])

    for u, v, data in raw.edges(data=True):
        length_m = float(data.get("length", 0.0))
        speed_kmh = _parse_speed_kmh(data.get("maxspeed"))

        u_s, v_s = str(u), str(v)
        if g.has_edge(u_s, v_s):
            if length_m >= g[u_s][v_s]["length_m"]:
                continue  # keep the shorter of the parallel edges
        g.add_edge(u_s, v_s, length_m=length_m, speed_kmh=speed_kmh)

    return g


def _parse_speed_kmh(maxspeed) -> float:
    """OSM's `maxspeed` tag is inconsistent (missing, a list, 'walk',
    'RO:urban', etc.) -- fall back to a sensible default rather than
    failing the whole import over one malformed tag."""
    default = 40.0
    if maxspeed is None:
        return default
    if isinstance(maxspeed, list):
        maxspeed = maxspeed[0] if maxspeed else None
    try:
        digits = "".join(ch for ch in str(maxspeed) if ch.isdigit())
        return float(digits) if digits else default
    except (ValueError, TypeError):
        return default


def graph_to_dict(g: nx.DiGraph) -> dict:
    return {
        "nodes": [{"id": n, **g.nodes[n]} for n in g.nodes],
        "edges": [{"u": u, "v": v, **g[u][v]} for u, v in g.edges],
    }


def dict_to_graph(data: dict) -> nx.DiGraph:
    g = nx.DiGraph()
    for n in data["nodes"]:
        node_id = n.pop("id")
        g.add_node(node_id, **n)
    for e in data["edges"]:
        g.add_edge(e["u"], e["v"], length_m=e["length_m"], speed_kmh=e["speed_kmh"])
    return g


def _s3_client():
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url or None,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )


def save_graph_to_storage(g: nx.DiGraph, storage_key: str) -> str:
    """
    Object storage abstraction. Backend is chosen via
    OBJECT_STORAGE_BACKEND=filesystem|s3 (see .env.example) -- nothing
    outside this module needs to know which one is active.

    filesystem: fine for local dev only. It does NOT survive container
    restarts/redeploys and is NOT shared across multiple API/worker
    instances, so it must not be used in a public multi-instance deployment.

    s3: use for any public deployment. storage_uri becomes an "s3://" URI
    instead of a filesystem path.
    """
    payload = json.dumps(graph_to_dict(g)).encode("utf-8")

    if settings.object_storage_backend == "s3":
        _s3_client().put_object(Bucket=settings.s3_bucket, Key=storage_key, Body=payload)
        return f"s3://{settings.s3_bucket}/{storage_key}"

    base = settings.object_storage_path
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, storage_key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(payload)
    return path


def load_graph_from_storage(storage_uri: str) -> nx.DiGraph:
    if storage_uri.startswith("s3://"):
        _, _, rest = storage_uri.partition("s3://")
        bucket, _, key = rest.partition("/")
        obj = _s3_client().get_object(Bucket=bucket, Key=key)
        data = json.loads(obj["Body"].read())
        return dict_to_graph(data)

    with open(storage_uri) as f:
        data = json.load(f)
    return dict_to_graph(data)


def validate_graph(g: nx.DiGraph) -> dict:
    is_connected = nx.is_weakly_connected(g) if g.number_of_nodes() > 0 else False
    return {
        "node_count": g.number_of_nodes(),
        "edge_count": g.number_of_edges(),
        "is_connected": is_connected,
    }
