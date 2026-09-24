from pydantic import BaseModel, model_validator


class DirectionsPoint(BaseModel):
    """Either an address (geocoded server-side) or raw lat/lon -- exactly
    one of the two must be given."""
    address: str | None = None
    lat: float | None = None
    lon: float | None = None

    @model_validator(mode="after")
    def _one_of_address_or_coords(self):
        has_address = bool(self.address and self.address.strip())
        has_coords = self.lat is not None and self.lon is not None
        if has_address == has_coords:  # both or neither
            raise ValueError("Provide either 'address', or both 'lat' and 'lon' -- not both forms, not neither.")
        return self


class DirectionsRequest(BaseModel):
    origin: DirectionsPoint
    destination: DirectionsPoint
    criterion: str = "time"  # "time" or "distance"
    alternates: bool = True


class ResolvedPoint(BaseModel):
    lat: float
    lon: float
    label: str


class RouteOption(BaseModel):
    rank: int
    is_primary: bool
    distance_m: float
    duration_s: float
    geometry: list[list[float]]  # [[lon, lat], ...] -- GeoJSON coordinate order


class DirectionsResponse(BaseModel):
    origin: ResolvedPoint
    destination: ResolvedPoint
    criterion: str
    routes: list[RouteOption]
