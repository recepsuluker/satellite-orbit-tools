"""Orbit propagation engine using SGP4 and Skyfield."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sgp4.api import WGS72, Satrec, jday

from satorbit.logging_config import get_logger

logger = get_logger("engine.orbit_propagator")


@dataclass
class SatellitePosition:
    """Single position of a satellite at a given time."""

    timestamp: datetime
    latitude: float
    longitude: float
    altitude_km: float
    x_km: float = 0.0
    y_km: float = 0.0
    z_km: float = 0.0
    vx_km_s: float = 0.0
    vy_km_s: float = 0.0
    vz_km_s: float = 0.0


@dataclass
class PropagationResult:
    """Result of orbit propagation for a single satellite."""

    norad_id: int
    name: str
    positions: list[SatellitePosition] = field(default_factory=list)
    error: str | None = None


def tle_to_satrec(tle_line1: str, tle_line2: str) -> Satrec:
    """Parse TLE lines into an SGP4 satellite record."""
    return Satrec.twoline2rv(tle_line1, tle_line2, WGS72)


def _ecef_to_geodetic(x_km: float, y_km: float, z_km: float) -> tuple[float, float, float]:
    """Convert ECEF coordinates to geodetic (lat, lon, alt)."""
    a = 6378.137  # Earth equatorial radius in km
    f = 1 / 298.257223563
    b = a * (1 - f)
    e2 = 1 - (b * b) / (a * a)

    lon = math.atan2(y_km, x_km)
    p = math.sqrt(x_km**2 + y_km**2)

    # Iterative approach
    lat = math.atan2(z_km, p * (1 - e2))
    for _ in range(10):
        sin_lat = math.sin(lat)
        N = a / math.sqrt(1 - e2 * sin_lat**2)
        lat = math.atan2(z_km + e2 * N * sin_lat, p)

    sin_lat = math.sin(lat)
    N = a / math.sqrt(1 - e2 * sin_lat**2)
    alt = p / math.cos(lat) - N

    return math.degrees(lat), math.degrees(lon), alt


def _gmst(jd: float, jd_fraction: float) -> float:
    """Calculate Greenwich Mean Sidereal Time in radians."""
    t_ut1 = (jd + jd_fraction - 2451545.0) / 36525.0
    gmst_sec = (
        67310.54841 + (876600.0 * 3600 + 8640184.812866) * t_ut1 + 0.093104 * t_ut1**2 - 6.2e-6 * t_ut1**3
    )
    gmst_rad = (gmst_sec % 86400) / 86400 * 2 * math.pi
    return gmst_rad


def propagate_satellite(
    tle_line1: str,
    tle_line2: str,
    start_time: datetime | None = None,
    duration_hours: float = 24.0,
    step_minutes: float = 1.0,
    name: str = "UNKNOWN",
) -> PropagationResult:
    """Propagate a satellite orbit from TLE data.

    Returns positions at each time step with geodetic coordinates and ECI vectors.
    """
    if start_time is None:
        start_time = datetime.now(timezone.utc)

    try:
        sat = tle_to_satrec(tle_line1, tle_line2)
    except Exception as e:
        logger.error("Failed to parse TLE for %s: %s", name, e)
        return PropagationResult(norad_id=0, name=name, error=str(e))

    norad_id = int(tle_line2.split()[1]) if len(tle_line2.split()) > 1 else 0
    result = PropagationResult(norad_id=norad_id, name=name)
    steps = int(duration_hours * 60 / step_minutes)

    for i in range(steps + 1):
        dt = start_time + timedelta(minutes=i * step_minutes)
        jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond / 1e6)

        error_code, position, velocity = sat.sgp4(jd, fr)
        if error_code != 0:
            continue

        x, y, z = position  # TEME coordinates in km
        vx, vy, vz = velocity  # km/s

        # TEME -> ECEF rotation
        theta = _gmst(jd, fr)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        x_ecef = cos_t * x + sin_t * y
        y_ecef = -sin_t * x + cos_t * y
        z_ecef = z

        lat, lon, alt = _ecef_to_geodetic(x_ecef, y_ecef, z_ecef)

        result.positions.append(
            SatellitePosition(
                timestamp=dt,
                latitude=lat,
                longitude=lon,
                altitude_km=alt,
                x_km=x,
                y_km=y,
                z_km=z,
                vx_km_s=vx,
                vy_km_s=vy,
                vz_km_s=vz,
            )
        )

    logger.info("Propagated %s: %d positions over %.1f hours", name, len(result.positions), duration_hours)
    return result


def propagate_batch(
    satellites: list[tuple[str, str, str]],
    start_time: datetime | None = None,
    duration_hours: float = 24.0,
    step_minutes: float = 1.0,
) -> list[PropagationResult]:
    """Propagate multiple satellites. Each tuple is (name, tle_line1, tle_line2)."""
    results = []
    for name, line1, line2 in satellites:
        result = propagate_satellite(line1, line2, start_time, duration_hours, step_minutes, name)
        results.append(result)
    logger.info("Batch propagation complete: %d satellites", len(results))
    return results
