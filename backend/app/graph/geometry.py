"""
Builds route geometry (LineString/MultiLineString) from graph node paths.
Route geometry is ALWAYS derived from the backend graph -- never accepted
as authoritative from the frontend.
"""
from __future__ import annotations

import networkx as nx
from geoalchemy2.shape import from_shape
from shapely.geometry import LineString


def path_to_linestring(g: nx.DiGraph, path: list[str]):
    coords = [(g.nodes[n]["lon"], g.nodes[n]["lat"]) for n in path]
    if len(coords) < 2:
        return None
    return from_shape(LineString(coords), srid=4326)
