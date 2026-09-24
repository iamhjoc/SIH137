"""
Geocoding adapters: address string -> (lat, lon).

>>> HOW TO ADD YOUR API KEY <<<
Put it in your real .env file (copy from .env.example), NOT in this file:
    GEOCODING_PROVIDER=google        # or "mappls" or "nominatim"
    GEOCODING_API_KEY=your-key-here

Nothing in this module needs editing to use your key -- the adapter
classes below read it from app.core.config.get_settings() at call time.
Only add code here if you need a provider that isn't one of these three.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.core.exceptions import ValidationAppError

settings = get_settings()


@dataclass(frozen=True)
class GeocodeResult:
    latitude: float
    longitude: float
    formatted_address: str
    confidence: float | None = None


class GeocodingAdapter(ABC):
    @abstractmethod
    async def geocode(self, address: str) -> GeocodeResult:
        ...


class NominatimGeocodingAdapter(GeocodingAdapter):
    """
    Free, no API key required. Public instance is rate-limited to ~1
    request/second and requires a descriptive User-Agent (OSM policy) --
    for any real production volume, self-host Nominatim or switch
    GEOCODING_PROVIDER to a paid provider instead.
    """
    BASE_URL = "https://nominatim.openstreetmap.org/search"

    async def geocode(self, address: str) -> GeocodeResult:
        base = settings.geocoding_api_base_url or self.BASE_URL
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                base,
                params={"q": address, "format": "json", "limit": 1, "countrycodes": "in"},
                headers={"User-Agent": "SIH26137-traffic-platform/1.0"},
            )
        resp.raise_for_status()
        results = resp.json()
        if not results:
            raise ValidationAppError(f"Could not geocode address: {address!r}")
        r = results[0]
        return GeocodeResult(
            latitude=float(r["lat"]), longitude=float(r["lon"]),
            formatted_address=r.get("display_name", address), confidence=float(r.get("importance", 0.5)),
        )


class GoogleGeocodingAdapter(GeocodingAdapter):
    """Requires GEOCODING_API_KEY -- a Google Cloud API key with the
    'Geocoding API' enabled. https://console.cloud.google.com/"""
    BASE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

    async def geocode(self, address: str) -> GeocodeResult:
        if not settings.geocoding_api_key:
            raise ValidationAppError("GEOCODING_API_KEY is not configured for provider 'google'.")
        base = settings.geocoding_api_base_url or self.BASE_URL
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(base, params={"address": address, "key": settings.geocoding_api_key, "region": "in"})
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "OK" or not data.get("results"):
            raise ValidationAppError(f"Could not geocode address: {address!r} ({data.get('status')})")
        result = data["results"][0]
        loc = result["geometry"]["location"]
        return GeocodeResult(latitude=loc["lat"], longitude=loc["lng"], formatted_address=result.get("formatted_address", address))


class MapplsGeocodingAdapter(GeocodingAdapter):
    """Requires GEOCODING_API_KEY -- a Mappls (MapmyIndia) REST API key.
    https://apis.mappls.com/console/  Often better than global providers
    for Indian address formats/landmarks."""
    BASE_URL = "https://atlas.mappls.com/api/places/geocode"

    async def geocode(self, address: str) -> GeocodeResult:
        if not settings.geocoding_api_key:
            raise ValidationAppError("GEOCODING_API_KEY is not configured for provider 'mappls'.")
        base = settings.geocoding_api_base_url or self.BASE_URL
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                base, params={"address": address},
                headers={"Authorization": f"Bearer {settings.geocoding_api_key}"},
            )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("copResults") or data.get("results") or []
        if not results:
            raise ValidationAppError(f"Could not geocode address: {address!r}")
        r = results[0]
        return GeocodeResult(
            latitude=float(r["latitude"]), longitude=float(r["longitude"]),
            formatted_address=r.get("formattedAddress", address),
        )


def get_geocoding_adapter() -> GeocodingAdapter:
    """Factory switched by GEOCODING_PROVIDER in your .env file."""
    provider = settings.geocoding_provider.lower()
    if provider == "google":
        return GoogleGeocodingAdapter()
    if provider == "mappls":
        return MapplsGeocodingAdapter()
    return NominatimGeocodingAdapter()
