"""Collision detection engine — finds close approaches between satellites."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

from satorbit.engine.orbit_propagator import PropagationResult, SatellitePosition
from satorbit.logging_config import get_logger

logger = get_logger("engine.collision_detector")


@dataclass
class ConjunctionEvent:
    """A close approach (conjunction) event between two satellites."""

    time: datetime
    satellite_a: str
    satellite_b: str
    norad_id_a: int
    norad_id_b: int
    distance_km: float
    relative_velocity_km_s: float
    risk_score: float  # 0-100, higher = more dangerous
    pos_a: tuple[float, float, float] = (0, 0, 0)  # lat, lon, alt
    pos_b: tuple[float, float, float] = (0, 0, 0)


@dataclass
class CollisionAnalysis:
    """Complete collision analysis result."""

    total_pairs_checked: int = 0
    total_conjunctions: int = 0
    threshold_km: float = 10.0
    analysis_duration_sec: float = 0.0
    events: list[ConjunctionEvent] = field(default_factory=list)
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0


def _distance_3d(p1: SatellitePosition, p2: SatellitePosition) -> float:
    """Calculate 3D Euclidean distance between two positions in km (ECI frame)."""
    return math.sqrt((p1.x_km - p2.x_km) ** 2 + (p1.y_km - p2.y_km) ** 2 + (p1.z_km - p2.z_km) ** 2)


def _relative_velocity(p1: SatellitePosition, p2: SatellitePosition) -> float:
    """Relative velocity magnitude between two satellites in km/s."""
    return math.sqrt(
        (p1.vx_km_s - p2.vx_km_s) ** 2 + (p1.vy_km_s - p2.vy_km_s) ** 2 + (p1.vz_km_s - p2.vz_km_s) ** 2
    )


def _calculate_risk_score(distance_km: float, relative_velocity_km_s: float) -> float:
    """Calculate a risk score (0-100) based on distance and relative velocity.

    - Distance < 1 km and high velocity → near 100
    - Distance > threshold → near 0
    """
    # Distance factor: exponential decay
    distance_factor = max(0, 100 * math.exp(-distance_km / 2.0))

    # Velocity factor: higher relative velocity = more dangerous
    velocity_factor = min(1.0, relative_velocity_km_s / 15.0)  # normalize to typical max

    score = distance_factor * (0.7 + 0.3 * velocity_factor)
    return round(min(100.0, max(0.0, score)), 2)


def check_conjunction_pair(
    result_a: PropagationResult,
    result_b: PropagationResult,
    threshold_km: float = 10.0,
) -> list[ConjunctionEvent]:
    """Check for conjunctions between two satellites."""
    events: list[ConjunctionEvent] = []

    if result_a.error or result_b.error:
        return events

    # Build time-indexed lookup for satellite B
    b_positions: dict[str, SatellitePosition] = {}
    for pos in result_b.positions:
        key = pos.timestamp.strftime("%Y%m%d%H%M%S")
        b_positions[key] = pos

    min_distance = float("inf")

    for pos_a in result_a.positions:
        key = pos_a.timestamp.strftime("%Y%m%d%H%M%S")
        pos_b = b_positions.get(key)
        if pos_b is None:
            continue

        dist = _distance_3d(pos_a, pos_b)

        if dist < threshold_km:
            rel_vel = _relative_velocity(pos_a, pos_b)
            risk = _calculate_risk_score(dist, rel_vel)

            event = ConjunctionEvent(
                time=pos_a.timestamp,
                satellite_a=result_a.name,
                satellite_b=result_b.name,
                norad_id_a=result_a.norad_id,
                norad_id_b=result_b.norad_id,
                distance_km=round(dist, 4),
                relative_velocity_km_s=round(rel_vel, 4),
                risk_score=risk,
                pos_a=(pos_a.latitude, pos_a.longitude, pos_a.altitude_km),
                pos_b=(pos_b.latitude, pos_b.longitude, pos_b.altitude_km),
            )
            events.append(event)

        if dist < min_distance:
            min_distance = dist

    return events


def analyze_collisions(
    propagation_results: list[PropagationResult],
    threshold_km: float = 10.0,
) -> CollisionAnalysis:
    """Perform full collision analysis across all satellite pairs."""
    import time

    start = time.time()
    analysis = CollisionAnalysis(threshold_km=threshold_km)
    n = len(propagation_results)

    logger.info("Starting collision analysis for %d satellites (threshold=%.1f km)", n, threshold_km)

    for i in range(n):
        for j in range(i + 1, n):
            analysis.total_pairs_checked += 1
            events = check_conjunction_pair(
                propagation_results[i],
                propagation_results[j],
                threshold_km,
            )
            analysis.events.extend(events)

    analysis.total_conjunctions = len(analysis.events)
    analysis.analysis_duration_sec = round(time.time() - start, 3)

    # Categorize by risk
    for e in analysis.events:
        if e.risk_score >= 70:
            analysis.high_risk_count += 1
        elif e.risk_score >= 30:
            analysis.medium_risk_count += 1
        else:
            analysis.low_risk_count += 1

    # Sort by risk score descending
    analysis.events.sort(key=lambda e: e.risk_score, reverse=True)

    logger.info(
        "Collision analysis complete: %d pairs, %d conjunctions (high=%d, medium=%d, low=%d) in %.2fs",
        analysis.total_pairs_checked,
        analysis.total_conjunctions,
        analysis.high_risk_count,
        analysis.medium_risk_count,
        analysis.low_risk_count,
        analysis.analysis_duration_sec,
    )
    return analysis
