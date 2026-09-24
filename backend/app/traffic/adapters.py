"""
Real traffic provider adapters: for each graph edge, ask the provider
"what's the current speed on the road near this point?" and normalize
the answer into this project's {speed_kmh, congestion_factor} shape.

>>> HOW TO ADD YOUR API KEY <<<
Put it in your real .env file (copy from .env.example), NOT in this file:
    TRAFFIC_PROVIDER=tomtom          # or "here" / "mappls" / "simulated"
    TRAFFIC_API_KEY=your-key-here

Nothing in this module needs editing to use your key.

IMPORTANT -- cost/rate limits: these adapters make one HTTP request per
graph edge. For a demo-scale graph (hundreds of edges, per the bbox
guidance in graph/loader.py) this is fine on a free tier; for a full-city
graph it is not -- batch/cache aggressively (Redis, keyed by
graph_edge_id + time_bucket, per the architecture doc's caching
strategy) before pointing this at a large graph, or you will exhaust
your API quota in a single traffic-scenario refresh.
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

import httpx
import networkx as nx

from app.core.config import get_settings
from app.core.exceptions import ValidationAppError

settings = get_settings()


class TrafficProviderAdapter(ABC):
    @abstractmethod
    async def fetch(self, g: nx.DiGraph, seed: int) -> list[dict]:
        ...


class SimulatedTrafficAdapter(TrafficProviderAdapter):
    async def fetch(self, g: nx.DiGraph, seed: int) -> list[dict]:
        from app.traffic.simulator import generate_traffic
        return generate_traffic(g, seed)


def _edge_midpoint(g: nx.DiGraph, u: str, v: str) -> tuple[float, float]:
    a, b = g.nodes[u], g.nodes[v]
    return (a["lat"] + b["lat"]) / 2, (a["lon"] + b["lon"]) / 2


class TomTomTrafficAdapter(TrafficProviderAdapter):
    """
    TomTom "Flow Segment Data" API -- given a point, returns the current
    speed of the nearest road segment. https://developer.tomtom.com/
    Free tier: 2,500 requests/day, which comfortably covers a demo-scale
    graph (a few hundred edges) refreshed a handful of times per day.
    """
    BASE_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"

    async def fetch(self, g: nx.DiGraph, seed: int) -> list[dict]:
        if not settings.traffic_api_key:
            raise ValidationAppError("TRAFFIC_API_KEY is not configured for provider 'tomtom'.")

        base = settings.traffic_api_base_url or self.BASE_URL
        records: list[dict] = []
        semaphore = asyncio.Semaphore(5)  # be polite to the free-tier rate limit

        async def fetch_edge(client: httpx.AsyncClient, u: str, v: str, free_flow_speed: float):
            lat, lon = _edge_midpoint(g, u, v)
            async with semaphore:
                try:
                    resp = await client.get(base, params={"point": f"{lat},{lon}", "key": settings.traffic_api_key})
                    resp.raise_for_status()
                    data = resp.json()["flowSegmentData"]
                    current_speed = float(data["currentSpeed"])
                    free_flow = float(data.get("freeFlowSpeed", free_flow_speed)) or free_flow_speed
                    congestion_factor = max(min(current_speed / max(free_flow, 1.0), 1.0), 0.05)
                    confidence = float(data.get("confidence", 0.85))
                except (httpx.HTTPError, KeyError, ValueError):
                    # Provider hiccup or edge outside coverage -- fall back to
                    # free-flow (no congestion signal) rather than failing the
                    # whole scenario refresh over one edge.
                    current_speed, congestion_factor, confidence = free_flow_speed, 1.0, 0.3

                records.append({
                    "graph_edge_id": f"{u}->{v}",
                    "time_bucket": 0,  # TomTom's live endpoint has no time-bucket concept; see note below
                    "speed_kmh": current_speed,
                    "congestion_factor": congestion_factor,
                    "confidence": confidence,
                })

        async with httpx.AsyncClient(timeout=10) as client:
            tasks = [
                fetch_edge(client, u, v, data.get("speed_kmh", 40.0))
                for u, v, data in g.edges(data=True)
            ]
            await asyncio.gather(*tasks)

        return records


class HereTrafficAdapter(TrafficProviderAdapter):
    """
    HERE Traffic API v7 flow endpoint. https://platform.here.com/
    Response shape varies by plan -- adjust the JSON parsing below to
    match your specific HERE subscription's response before using this
    in production; the request shape (point-based flow query) is correct
    for the standard v7 flow API as of this writing.
    """
    BASE_URL = "https://data.traffic.hereapi.com/v7/flow"

    async def fetch(self, g: nx.DiGraph, seed: int) -> list[dict]:
        if not settings.traffic_api_key:
            raise ValidationAppError("TRAFFIC_API_KEY is not configured for provider 'here'.")

        base = settings.traffic_api_base_url or self.BASE_URL
        records: list[dict] = []
        semaphore = asyncio.Semaphore(5)

        async def fetch_edge(client: httpx.AsyncClient, u: str, v: str, free_flow_speed: float):
            lat, lon = _edge_midpoint(g, u, v)
            async with semaphore:
                try:
                    resp = await client.get(base, params={
                        "in": f"circle:{lat},{lon};r=50", "locationReferencing": "shape", "apiKey": settings.traffic_api_key,
                    })
                    resp.raise_for_status()
                    result = resp.json()["results"][0]["currentFlow"]
                    current_speed = float(result["speed"]) * 3.6  # HERE returns m/s
                    free_flow = float(result.get("freeFlow", free_flow_speed / 3.6)) * 3.6
                    congestion_factor = max(min(current_speed / max(free_flow, 1.0), 1.0), 0.05)
                    confidence = float(result.get("confidence", 0.8))
                except (httpx.HTTPError, KeyError, IndexError, ValueError):
                    current_speed, congestion_factor, confidence = free_flow_speed, 1.0, 0.3

                records.append({
                    "graph_edge_id": f"{u}->{v}", "time_bucket": 0,
                    "speed_kmh": current_speed, "congestion_factor": congestion_factor, "confidence": confidence,
                })

        async with httpx.AsyncClient(timeout=10) as client:
            tasks = [fetch_edge(client, u, v, data.get("speed_kmh", 40.0)) for u, v, data in g.edges(data=True)]
            await asyncio.gather(*tasks)

        return records


class MapplsTrafficAdapter(TrafficProviderAdapter):
    """
    Mappls (MapmyIndia) Traffic API. https://apis.mappls.com/console/
    Endpoint/response shape below is indicative -- confirm against your
    specific Mappls plan's API docs and adjust the JSON keys accordingly.
    """
    BASE_URL = "https://apis.mappls.com/advancedmaps/v1/traffic/flow"

    async def fetch(self, g: nx.DiGraph, seed: int) -> list[dict]:
        if not settings.traffic_api_key:
            raise ValidationAppError("TRAFFIC_API_KEY is not configured for provider 'mappls'.")

        base = settings.traffic_api_base_url or self.BASE_URL
        records: list[dict] = []
        semaphore = asyncio.Semaphore(5)

        async def fetch_edge(client: httpx.AsyncClient, u: str, v: str, free_flow_speed: float):
            lat, lon = _edge_midpoint(g, u, v)
            async with semaphore:
                try:
                    resp = await client.get(
                        f"{base}/{lat}/{lon}",
                        headers={"Authorization": f"Bearer {settings.traffic_api_key}"},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    current_speed = float(data["currentSpeed"])
                    free_flow = float(data.get("freeFlowSpeed", free_flow_speed))
                    congestion_factor = max(min(current_speed / max(free_flow, 1.0), 1.0), 0.05)
                except (httpx.HTTPError, KeyError, ValueError):
                    current_speed, congestion_factor = free_flow_speed, 1.0

                records.append({
                    "graph_edge_id": f"{u}->{v}", "time_bucket": 0,
                    "speed_kmh": current_speed, "congestion_factor": congestion_factor, "confidence": 0.75,
                })

        async with httpx.AsyncClient(timeout=10) as client:
            tasks = [fetch_edge(client, u, v, data.get("speed_kmh", 40.0)) for u, v, data in g.edges(data=True)]
            await asyncio.gather(*tasks)

        return records


def get_traffic_adapter() -> TrafficProviderAdapter:
    """Factory switched by TRAFFIC_PROVIDER in your .env file."""
    provider = settings.traffic_provider.lower()
    if provider == "tomtom":
        return TomTomTrafficAdapter()
    if provider == "here":
        return HereTrafficAdapter()
    if provider == "mappls":
        return MapplsTrafficAdapter()
    return SimulatedTrafficAdapter()
