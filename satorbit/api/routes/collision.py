"""Collision detection API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from satorbit.config import get_settings
from satorbit.database.manager import SatelliteDB
from satorbit.engine.cache import cache_get, cache_set
from satorbit.engine.collision_detector import analyze_collisions, check_conjunction_pair
from satorbit.engine.orbit_propagator import propagate_satellite
from satorbit.logging_config import get_logger

logger = get_logger("api.collision")
router = APIRouter()


class CollisionRequest(BaseModel):
    norad_ids: list[int]
    threshold_km: float = 10.0
    duration_hours: float = 24.0
    step_minutes: float = 1.0


@router.post("/analyze")
async def analyze_collision(request: CollisionRequest):
    """Run collision analysis on a set of satellites."""
    if len(request.norad_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 satellites required")
    if len(request.norad_ids) > 200:
        raise HTTPException(status_code=400, detail="Maximum 200 satellites per analysis")

    # Check cache
    cache_key = f"{sorted(request.norad_ids)}:{request.threshold_km}:{request.duration_hours}"
    cached = cache_get("collision", cache_key)
    if cached:
        return cached

    # Fetch TLE data
    with SatelliteDB() as db:
        satellites = []
        missing = []
        for nid in request.norad_ids:
            sat = db.get_satellite(nid)
            if sat:
                satellites.append(sat)
            else:
                missing.append(nid)

    if missing:
        logger.warning("Missing satellites from catalog: %s", missing)

    if len(satellites) < 2:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 2 satellites in catalog. Missing: {missing}",
        )

    # Propagate orbits
    propagations = []
    for sat in satellites:
        result = propagate_satellite(
            sat["tle_line1"],
            sat["tle_line2"],
            duration_hours=request.duration_hours,
            step_minutes=request.step_minutes,
            name=sat["name"],
        )
        if not result.error:
            propagations.append(result)

    # Run collision analysis
    analysis = analyze_collisions(propagations, request.threshold_km)

    # Save events to database
    with SatelliteDB() as db:
        for event in analysis.events:
            db.save_conjunction_event(
                {
                    "event_time": event.time.isoformat(),
                    "satellite_a_id": event.norad_id_a,
                    "satellite_b_id": event.norad_id_b,
                    "distance_km": event.distance_km,
                    "relative_vel": event.relative_velocity_km_s,
                    "risk_score": event.risk_score,
                    "lat_a": event.pos_a[0],
                    "lon_a": event.pos_a[1],
                    "alt_a": event.pos_a[2],
                    "lat_b": event.pos_b[0],
                    "lon_b": event.pos_b[1],
                    "alt_b": event.pos_b[2],
                }
            )

    response = {
        "total_pairs_checked": analysis.total_pairs_checked,
        "total_conjunctions": analysis.total_conjunctions,
        "threshold_km": analysis.threshold_km,
        "analysis_duration_sec": analysis.analysis_duration_sec,
        "high_risk": analysis.high_risk_count,
        "medium_risk": analysis.medium_risk_count,
        "low_risk": analysis.low_risk_count,
        "events": [
            {
                "time": e.time.isoformat(),
                "satellite_a": e.satellite_a,
                "satellite_b": e.satellite_b,
                "norad_id_a": e.norad_id_a,
                "norad_id_b": e.norad_id_b,
                "distance_km": e.distance_km,
                "relative_velocity_km_s": e.relative_velocity_km_s,
                "risk_score": e.risk_score,
            }
            for e in analysis.events
        ],
    }

    # Cache result
    settings = get_settings()
    cache_set("collision", cache_key, value=response, ttl=settings.analysis_cache_ttl)

    return response


@router.get("/history")
async def collision_history(limit: int = Query(50, ge=1, le=500)):
    """Get recent conjunction events from database."""
    with SatelliteDB() as db:
        events = db.get_recent_conjunctions(limit)
    return {"events": events, "count": len(events)}


@router.post("/quick-check")
async def quick_check(
    norad_id_a: int,
    norad_id_b: int,
    threshold_km: float = Query(10.0, ge=0.1),
    duration_hours: float = Query(24.0, ge=0.1, le=168),
):
    """Quick collision check between two specific satellites."""
    with SatelliteDB() as db:
        sat_a = db.get_satellite(norad_id_a)
        sat_b = db.get_satellite(norad_id_b)

    if not sat_a:
        raise HTTPException(status_code=404, detail=f"Satellite {norad_id_a} not found")
    if not sat_b:
        raise HTTPException(status_code=404, detail=f"Satellite {norad_id_b} not found")

    prop_a = propagate_satellite(
        sat_a["tle_line1"], sat_a["tle_line2"], duration_hours=duration_hours, name=sat_a["name"]
    )
    prop_b = propagate_satellite(
        sat_b["tle_line1"], sat_b["tle_line2"], duration_hours=duration_hours, name=sat_b["name"]
    )

    events = check_conjunction_pair(prop_a, prop_b, threshold_km)

    return {
        "satellite_a": sat_a["name"],
        "satellite_b": sat_b["name"],
        "threshold_km": threshold_km,
        "conjunction_count": len(events),
        "events": [
            {
                "time": e.time.isoformat(),
                "distance_km": e.distance_km,
                "relative_velocity_km_s": e.relative_velocity_km_s,
                "risk_score": e.risk_score,
            }
            for e in events
        ],
    }
