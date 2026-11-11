"""Satellite catalog API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from satorbit.database.manager import SatelliteDB
from satorbit.logging_config import get_logger

logger = get_logger("api.satellites")
router = APIRouter()


class SatelliteResponse(BaseModel):
    norad_id: int
    name: str
    intl_designator: str | None = None
    tle_line1: str
    tle_line2: str
    inclination: float | None = None
    eccentricity: float | None = None
    period_min: float | None = None
    apogee_km: float | None = None
    perigee_km: float | None = None
    object_type: str | None = None
    country_code: str | None = None


class CatalogStats(BaseModel):
    total: int
    by_type: list[dict]


@router.get("/", response_model=list[SatelliteResponse])
async def list_satellites(
    query: str = Query("", description="Search by name or NORAD ID"),
    object_type: str | None = Query(None, description="Filter by object type"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Search and list satellites in the catalog."""
    with SatelliteDB() as db:
        results = db.search_satellites(query, object_type, limit, offset)
    return results


@router.get("/stats", response_model=CatalogStats)
async def catalog_stats():
    """Get catalog statistics."""
    with SatelliteDB() as db:
        total = db.get_satellite_count()
        by_type = db.get_object_type_stats()
    return {"total": total, "by_type": by_type}


@router.get("/{norad_id}", response_model=SatelliteResponse)
async def get_satellite(norad_id: int):
    """Get a specific satellite by NORAD ID."""
    with SatelliteDB() as db:
        sat = db.get_satellite(norad_id)
    if not sat:
        raise HTTPException(status_code=404, detail=f"Satellite {norad_id} not found")
    return sat


@router.get("/{norad_id}/position")
async def get_satellite_position(
    norad_id: int,
    duration_hours: float = Query(1.0, ge=0.1, le=168),
    step_minutes: float = Query(1.0, ge=0.1, le=60),
):
    """Propagate satellite orbit and return positions."""
    with SatelliteDB() as db:
        sat = db.get_satellite(norad_id)
    if not sat:
        raise HTTPException(status_code=404, detail=f"Satellite {norad_id} not found")

    from satorbit.engine.orbit_propagator import propagate_satellite

    result = propagate_satellite(
        sat["tle_line1"],
        sat["tle_line2"],
        duration_hours=duration_hours,
        step_minutes=step_minutes,
        name=sat["name"],
    )

    if result.error:
        raise HTTPException(status_code=500, detail=f"Propagation error: {result.error}")

    return {
        "norad_id": norad_id,
        "name": sat["name"],
        "position_count": len(result.positions),
        "positions": [
            {
                "time": p.timestamp.isoformat(),
                "lat": round(p.latitude, 4),
                "lon": round(p.longitude, 4),
                "alt_km": round(p.altitude_km, 2),
            }
            for p in result.positions
        ],
    }
