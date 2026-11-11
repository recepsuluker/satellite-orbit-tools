"""Guardian agent: conjunction screening for the satellites tracked in Mission Control.

Propagates every tracked satellite with SGP4 and screens all pairs for close
approaches using :mod:`satorbit.engine.collision_detector`. The closest approach
of each pair is written to ``conjunction-warning.csv``, which the dashboard,
chat and Notify agent read.
"""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path

from satorbit.engine.collision_detector import analyze_collisions
from satorbit.engine.orbit_propagator import propagate_satellite

from . import paths
from .utils import get_satellite_from_catalog, load_config

logger = logging.getLogger(__name__)

CSV_FIELDS = [
    "satellite_1",
    "satellite_2",
    "norad_1",
    "norad_2",
    "distance_km",
    "relative_velocity_km_s",
    "risk_score",
    "time_utc",
]


def run_conjunction_scan(
    threshold_km: float | None = None,
    hours: float | None = None,
    step_minutes: float = 1.0,
    output: Path = paths.CONJUNCTION_CSV,
    start_time: datetime | None = None,
) -> int:
    """Screen tracked satellites for conjunctions and write the CSV.

    Returns the number of satellite pairs with a close approach below the threshold.
    """
    config = load_config()
    settings = config.get("settings", {})
    if threshold_km is None:
        threshold_km = float(settings.get("conjunction_threshold_km", 10.0))
    if hours is None:
        hours = 24.0 * float(settings.get("prediction_days", 1))

    results = []
    for sat in config.get("satellites", []):
        tle = get_satellite_from_catalog(sat["norad_id"])
        if not tle:
            logger.warning("No TLE available for %s; skipping", sat.get("name", sat["norad_id"]))
            continue
        result = propagate_satellite(
            tle[1],
            tle[2],
            start_time=start_time,
            duration_hours=hours,
            step_minutes=step_minutes,
            name=tle[0].strip(),
        )
        result.norad_id = int(sat["norad_id"])
        results.append(result)

    rows = []
    if len(results) >= 2:
        analysis = analyze_collisions(results, threshold_km=threshold_km)
        closest = {}
        for event in analysis.events:
            key = (event.norad_id_a, event.norad_id_b)
            if key not in closest or event.distance_km < closest[key].distance_km:
                closest[key] = event
        for event in sorted(closest.values(), key=lambda e: e.distance_km):
            rows.append(
                {
                    "satellite_1": event.satellite_a,
                    "satellite_2": event.satellite_b,
                    "norad_1": event.norad_id_a,
                    "norad_2": event.norad_id_b,
                    "distance_km": event.distance_km,
                    "relative_velocity_km_s": event.relative_velocity_km_s,
                    "risk_score": event.risk_score,
                    "time_utc": event.time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

    tmp = output.with_suffix(".tmp")
    with tmp.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(output)
    logger.info("Conjunction scan: %d satellites, %d close pairs", len(results), len(rows))
    return len(rows)
