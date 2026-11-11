"""Visibility/pass prediction calculator for ground stations."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

from satorbit.engine.orbit_propagator import PropagationResult, SatellitePosition
from satorbit.logging_config import get_logger

logger = get_logger("engine.visibility")

EARTH_RADIUS_KM = 6371.0


@dataclass
class GroundStation:
    """Ground station definition."""

    name: str
    latitude: float
    longitude: float
    elevation_m: float = 0.0


@dataclass
class PassEvent:
    """A single satellite pass over a ground station."""

    satellite_name: str
    norad_id: int
    aos_time: datetime  # Acquisition of Signal (rise)
    aos_azimuth: float
    max_time: datetime  # Maximum elevation
    max_elevation: float
    max_azimuth: float
    los_time: datetime  # Loss of Signal (set)
    los_azimuth: float
    duration_seconds: float
    max_distance_km: float


@dataclass
class VisibilityResult:
    """Visibility analysis result."""

    station: GroundStation
    satellite_name: str
    passes: list[PassEvent] = field(default_factory=list)
    analysis_window_hours: float = 0.0


def _geodetic_to_ecef(lat_deg: float, lon_deg: float, alt_km: float) -> tuple[float, float, float]:
    """Convert geodetic to ECEF coordinates."""
    a = 6378.137
    f = 1 / 298.257223563
    e2 = 2 * f - f * f

    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    sin_lon = math.sin(lon)
    cos_lon = math.cos(lon)

    N = a / math.sqrt(1 - e2 * sin_lat**2)
    x = (N + alt_km) * cos_lat * cos_lon
    y = (N + alt_km) * cos_lat * sin_lon
    z = (N * (1 - e2) + alt_km) * sin_lat
    return x, y, z


def _calculate_look_angle(
    station: GroundStation,
    sat_pos: SatellitePosition,
) -> tuple[float, float, float]:
    """Calculate azimuth, elevation, and range from station to satellite.

    Returns (azimuth_deg, elevation_deg, range_km).
    """
    # Station position in ECEF
    station_alt_km = station.elevation_m / 1000.0
    sx, sy, sz = _geodetic_to_ecef(station.latitude, station.longitude, station_alt_km)

    # Satellite position in ECEF (approximate from geodetic)
    tx, ty, tz = _geodetic_to_ecef(sat_pos.latitude, sat_pos.longitude, sat_pos.altitude_km)

    # Range vector in ECEF
    rx, ry, rz = tx - sx, ty - sy, tz - sz
    range_km = math.sqrt(rx**2 + ry**2 + rz**2)

    # Convert to local ENU (East-North-Up) frame
    lat = math.radians(station.latitude)
    lon = math.radians(station.longitude)
    sin_lat, cos_lat = math.sin(lat), math.cos(lat)
    sin_lon, cos_lon = math.sin(lon), math.cos(lon)

    east = -sin_lon * rx + cos_lon * ry
    north = -sin_lat * cos_lon * rx - sin_lat * sin_lon * ry + cos_lat * rz
    up = cos_lat * cos_lon * rx + cos_lat * sin_lon * ry + sin_lat * rz

    # Azimuth (from North, clockwise)
    azimuth = math.degrees(math.atan2(east, north)) % 360

    # Elevation above horizon
    horizontal = math.sqrt(east**2 + north**2)
    elevation = math.degrees(math.atan2(up, horizontal))

    return azimuth, elevation, range_km


def calculate_passes(
    propagation: PropagationResult,
    station: GroundStation,
    min_elevation: float = 10.0,
) -> VisibilityResult:
    """Calculate all passes of a satellite over a ground station.

    A pass starts when elevation exceeds min_elevation and ends when it drops below.
    """
    result = VisibilityResult(
        station=station,
        satellite_name=propagation.name,
    )

    if propagation.error or not propagation.positions:
        return result

    # Calculate time span
    t0 = propagation.positions[0].timestamp
    t1 = propagation.positions[-1].timestamp
    result.analysis_window_hours = (t1 - t0).total_seconds() / 3600

    in_pass = False
    pass_data: dict = {}

    for pos in propagation.positions:
        az, el, rng = _calculate_look_angle(station, pos)

        if el >= min_elevation:
            if not in_pass:
                # AOS
                in_pass = True
                pass_data = {
                    "aos_time": pos.timestamp,
                    "aos_azimuth": round(az, 2),
                    "max_elevation": el,
                    "max_azimuth": az,
                    "max_time": pos.timestamp,
                    "max_distance_km": rng,
                }
            if el > pass_data["max_elevation"]:
                pass_data["max_elevation"] = el
                pass_data["max_azimuth"] = az
                pass_data["max_time"] = pos.timestamp
                pass_data["max_distance_km"] = rng
        else:
            if in_pass:
                # LOS
                duration = (pos.timestamp - pass_data["aos_time"]).total_seconds()
                event = PassEvent(
                    satellite_name=propagation.name,
                    norad_id=propagation.norad_id,
                    aos_time=pass_data["aos_time"],
                    aos_azimuth=pass_data["aos_azimuth"],
                    max_time=pass_data["max_time"],
                    max_elevation=round(pass_data["max_elevation"], 2),
                    max_azimuth=round(pass_data["max_azimuth"], 2),
                    los_time=pos.timestamp,
                    los_azimuth=round(az, 2),
                    duration_seconds=round(duration, 1),
                    max_distance_km=round(pass_data["max_distance_km"], 2),
                )
                result.passes.append(event)
                in_pass = False

    logger.info(
        "Visibility for %s from %s: %d passes in %.1f hours",
        propagation.name,
        station.name,
        len(result.passes),
        result.analysis_window_hours,
    )
    return result
