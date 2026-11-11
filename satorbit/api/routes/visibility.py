"""Visibility/pass prediction API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from satorbit.database.manager import SatelliteDB
from satorbit.engine.orbit_propagator import propagate_satellite
from satorbit.engine.visibility_calculator import GroundStation, calculate_passes
from satorbit.logging_config import get_logger

logger = get_logger("api.visibility")
router = APIRouter()


class PassResponse(BaseModel):
    satellite_name: str
    norad_id: int
    aos_time: str
    aos_azimuth: float
    max_time: str
    max_elevation: float
    max_azimuth: float
    los_time: str
    los_azimuth: float
    duration_seconds: float


@router.get("/passes/{norad_id}")
async def predict_passes(
    norad_id: int,
    station_id: int | None = Query(None, description="Ground station ID (default: first station)"),
    lat: float | None = Query(None, description="Custom latitude"),
    lon: float | None = Query(None, description="Custom longitude"),
    elevation_m: float = Query(0.0),
    min_elevation: float = Query(10.0, ge=0, le=90),
    duration_hours: float = Query(24.0, ge=1, le=168),
):
    """Predict satellite passes over a ground station."""
    with SatelliteDB() as db:
        sat = db.get_satellite(norad_id)
        if not sat:
            raise HTTPException(status_code=404, detail=f"Satellite {norad_id} not found")

        # Determine ground station
        if lat is not None and lon is not None:
            station = GroundStation(
                name="Custom Location",
                latitude=lat,
                longitude=lon,
                elevation_m=elevation_m,
            )
        elif station_id:
            stations = db.get_ground_stations()
            station_data = next((s for s in stations if s["id"] == station_id), None)
            if not station_data:
                raise HTTPException(status_code=404, detail=f"Station {station_id} not found")
            station = GroundStation(
                name=station_data["name"],
                latitude=station_data["latitude"],
                longitude=station_data["longitude"],
                elevation_m=station_data["elevation_m"],
            )
        else:
            stations = db.get_ground_stations()
            if not stations:
                raise HTTPException(status_code=400, detail="No ground stations configured")
            s = stations[0]
            station = GroundStation(
                name=s["name"],
                latitude=s["latitude"],
                longitude=s["longitude"],
                elevation_m=s["elevation_m"],
            )

    # Propagate
    prop = propagate_satellite(
        sat["tle_line1"],
        sat["tle_line2"],
        duration_hours=duration_hours,
        step_minutes=0.5,  # 30-second resolution for pass detection
        name=sat["name"],
    )

    if prop.error:
        raise HTTPException(status_code=500, detail=f"Propagation error: {prop.error}")

    # Calculate passes
    result = calculate_passes(prop, station, min_elevation)

    return {
        "satellite": sat["name"],
        "norad_id": norad_id,
        "station": {
            "name": station.name,
            "lat": station.latitude,
            "lon": station.longitude,
        },
        "analysis_window_hours": result.analysis_window_hours,
        "pass_count": len(result.passes),
        "passes": [
            {
                "aos_time": p.aos_time.isoformat(),
                "aos_azimuth": p.aos_azimuth,
                "max_time": p.max_time.isoformat(),
                "max_elevation": p.max_elevation,
                "max_azimuth": p.max_azimuth,
                "los_time": p.los_time.isoformat(),
                "los_azimuth": p.los_azimuth,
                "duration_seconds": p.duration_seconds,
                "max_distance_km": p.max_distance_km,
            }
            for p in result.passes
        ],
    }


@router.get("/stations")
async def list_stations():
    """List all ground stations."""
    with SatelliteDB() as db:
        stations = db.get_ground_stations()
    return {"stations": stations}


@router.post("/stations")
async def add_station(
    name: str,
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    elevation_m: float = Query(0.0, ge=0),
    description: str = "",
):
    """Add a new ground station."""
    with SatelliteDB() as db:
        station_id = db.add_ground_station(name, latitude, longitude, elevation_m, description)
    return {"id": station_id, "name": name, "status": "created"}
