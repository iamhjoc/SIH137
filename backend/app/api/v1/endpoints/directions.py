from fastapi import APIRouter

from app.schemas.directions import DirectionsRequest, DirectionsResponse
from app.services import directions_service

router = APIRouter(prefix="/directions", tags=["directions"])


@router.post("", response_model=DirectionsResponse)
async def get_directions(payload: DirectionsRequest) -> DirectionsResponse:
    """Point-to-point route between an origin and destination -- either
    address may be given as free text (geocoded server-side, India-wide)
    or as raw lat/lon. Not tied to any project's pre-imported graph: pulls
    the road network for whatever area the two points fall in, on demand.
    """
    return await directions_service.get_directions(payload)
