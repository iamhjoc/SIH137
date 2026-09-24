"""
Point-to-point "directions" (source -> destination), distinct from the
multi-stop QPSO fleet optimizer. For exactly two points, "optimal" is a
plain shortest-path problem -- no swarm optimization needed or applicable.

Scoped to work for ANY address in India without ever loading a
country-scale graph: each request pulls only the OSM road network inside
a bounding box around its own origin/destination (see _get_or_import_graph
below), not a pre-seeded city. This is the same tradeoff real routing
backends make -- process only the area a request actually needs.

Known limitations (kept deliberately simple for this feature's scope):
  - The bbox graph cache below is in-process memory only: it is empty
    again on every restart and is NOT shared across multiple api/worker
    processes. A production version would persist imported graphs via
    the existing GraphVersion + object-storage pattern used elsewhere in
    this codebase (see graph_service.py / graph/loader.py) instead.
  - Very long routes (e.g. coast-to-coast) produce a very large bbox and
    a slow OSM pull -- this is built for regional routes, not
    thousand-kilometer ones.
  - map_coordinate_to_graph_node() is an O(n) nearest-node scan; fine at
    bbox-scoped size (thousands of nodes), would not scale to a
    country-wide graph.
"""
from __future__ import annotations

import itertools

import networkx as nx

from app.core.exceptions import NotFoundError, ValidationAppError
from app.geocoding.adapters import GeocodeResult, get_geocoding_adapter
from app.graph.loader import import_graph_from_bbox
from app.graph.mapper import map_coordinate_to_graph_node
from app.schemas.directions import DirectionsPoint, DirectionsRequest, DirectionsResponse, ResolvedPoint, RouteOption

MAX_ALTERNATES = 3
_GRAPH_CACHE: dict[tuple[float, float, float, float], nx.DiGraph] = {}
_CACHE_MAX_ENTRIES = 20


def _bbox_cache_key(north: float, south: float, east: float, west: float) -> tuple[float, float, float, float]:
    # Round to a ~1km grid so nearby requests reuse the same cached pull
    # instead of re-fetching OSM data for a near-identical area.
    return (round(north, 2), round(south, 2), round(east, 2), round(west, 2))


def _get_or_import_graph(lat1: float, lon1: float, lat2: float, lon2: float) -> nx.DiGraph:
    min_lat, max_lat = sorted((lat1, lat2))
    min_lon, max_lon = sorted((lon1, lon2))
    # Pad the bbox so the route can use real roads that bow outside the
    # dead-straight box between the two points, not just a straight line.
    lat_pad = max((max_lat - min_lat) * 0.35, 0.03)
    lon_pad = max((max_lon - min_lon) * 0.35, 0.03)
    north, south = max_lat + lat_pad, min_lat - lat_pad
    east, west = max_lon + lon_pad, min_lon - lon_pad

    key = _bbox_cache_key(north, south, east, west)
    cached = _GRAPH_CACHE.get(key)
    if cached is not None:
        return cached

    try:
        g = import_graph_from_bbox(north, south, east, west)
    except Exception as exc:
        raise ValidationAppError(
            "Could not fetch the road network for this area from OpenStreetMap. "
            "Try again, or use points closer together.",
            details={"error": str(exc)},
        ) from exc

    if g.number_of_nodes() == 0:
        raise ValidationAppError("No road network was found covering these two points.")

    if len(_GRAPH_CACHE) >= _CACHE_MAX_ENTRIES:
        _GRAPH_CACHE.pop(next(iter(_GRAPH_CACHE)))
    _GRAPH_CACHE[key] = g
    return g


def _annotate_travel_time(g: nx.DiGraph) -> None:
    """Adds a `travel_time_s` edge attribute derived from length_m/speed_kmh,
    so time-weighted shortest-path search can use a plain attribute name
    like distance-weighted search does, instead of a callable weight."""
    for _u, _v, data in g.edges(data=True):
        if "travel_time_s" not in data:
            speed = max(data.get("speed_kmh", 40.0), 1.0)
            data["travel_time_s"] = (data.get("length_m", 0.0) / 1000.0) / speed * 3600.0


async def _resolve_point(point: DirectionsPoint) -> ResolvedPoint:
    if point.address:
        adapter = get_geocoding_adapter()
        result: GeocodeResult = await adapter.geocode(point.address)
        return ResolvedPoint(lat=result.latitude, lon=result.longitude, label=result.formatted_address)
    return ResolvedPoint(lat=point.lat, lon=point.lon, label=f"{point.lat:.5f}, {point.lon:.5f}")


def _path_distance_m(g: nx.DiGraph, path: list[str]) -> float:
    return sum(g[u][v]["length_m"] for u, v in zip(path, path[1:]))


def _path_duration_s(g: nx.DiGraph, path: list[str]) -> float:
    return sum(g[u][v]["travel_time_s"] for u, v in zip(path, path[1:]))


def _path_geometry(g: nx.DiGraph, path: list[str]) -> list[list[float]]:
    return [[g.nodes[n]["lon"], g.nodes[n]["lat"]] for n in path]


async def get_directions(payload: DirectionsRequest) -> DirectionsResponse:
    if payload.criterion not in ("time", "distance"):
        raise ValidationAppError("criterion must be 'time' or 'distance'.")

    origin = await _resolve_point(payload.origin)
    destination = await _resolve_point(payload.destination)

    g = _get_or_import_graph(origin.lat, origin.lon, destination.lat, destination.lon)
    _annotate_travel_time(g)

    origin_node = map_coordinate_to_graph_node(g, origin.lat, origin.lon, max_distance_m=1500.0)
    dest_node = map_coordinate_to_graph_node(g, destination.lat, destination.lon, max_distance_m=1500.0)

    weight_attr = "travel_time_s" if payload.criterion == "time" else "length_m"
    limit = MAX_ALTERNATES if payload.alternates else 1

    try:
        paths_iter = nx.shortest_simple_paths(g, origin_node, dest_node, weight=weight_attr)
        paths = list(itertools.islice(paths_iter, limit))
    except nx.NodeNotFound as exc:
        raise NotFoundError("Origin or destination could not be located on the road network.") from exc
    except nx.NetworkXNoPath as exc:
        raise NotFoundError("No route exists between these two points on the available road network.") from exc

    routes = [
        RouteOption(
            rank=i,
            is_primary=(i == 0),
            distance_m=_path_distance_m(g, path),
            duration_s=_path_duration_s(g, path),
            geometry=_path_geometry(g, path),
        )
        for i, path in enumerate(paths)
    ]

    return DirectionsResponse(origin=origin, destination=destination, criterion=payload.criterion, routes=routes)
