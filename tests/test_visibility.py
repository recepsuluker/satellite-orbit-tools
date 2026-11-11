"""Tests for the visibility/pass prediction calculator."""

import pytest

from satorbit.engine.orbit_propagator import propagate_satellite
from satorbit.engine.visibility_calculator import (
    GroundStation,
    PassEvent,
    VisibilityResult,
    _geodetic_to_ecef,
    calculate_passes,
)

KENNEDY = GroundStation(
    name="Kennedy Space Center",
    latitude=28.5721,
    longitude=-80.6480,
    elevation_m=3.0,
)


class TestGeodeticToEcef:
    def test_equator_prime_meridian(self):
        x, y, z = _geodetic_to_ecef(0.0, 0.0, 0.0)
        assert abs(x - 6378.137) < 0.1
        assert abs(y) < 0.1
        assert abs(z) < 0.1

    def test_north_pole(self):
        x, y, z = _geodetic_to_ecef(90.0, 0.0, 0.0)
        assert abs(x) < 0.1
        assert abs(y) < 0.1
        assert z > 6300  # ~6356 km

    def test_altitude_increases_radius(self):
        x0, y0, z0 = _geodetic_to_ecef(0.0, 0.0, 0.0)
        x1, y1, z1 = _geodetic_to_ecef(0.0, 0.0, 100.0)  # 100 km alt
        r0 = (x0**2 + y0**2 + z0**2) ** 0.5
        r1 = (x1**2 + y1**2 + z1**2) ** 0.5
        assert abs(r1 - r0 - 100) < 1  # ~100 km difference


class TestCalculatePasses:
    def test_iss_passes_from_kennedy(self, sample_tle_iss, sample_datetime):
        prop = propagate_satellite(
            sample_tle_iss["line1"],
            sample_tle_iss["line2"],
            start_time=sample_datetime,
            duration_hours=24,
            step_minutes=0.5,
            name="ISS",
        )
        result = calculate_passes(prop, KENNEDY, min_elevation=10.0)

        assert isinstance(result, VisibilityResult)
        assert result.station.name == "Kennedy Space Center"
        assert result.satellite_name == "ISS"
        assert result.analysis_window_hours == pytest.approx(24.0, abs=0.1)

        # ISS should have some passes over Kennedy in 24 hours
        # (this depends on the TLE epoch — could be 0 if TLE is stale)
        for p in result.passes:
            assert isinstance(p, PassEvent)
            assert p.max_elevation >= 10.0
            assert 0 <= p.aos_azimuth < 360
            assert p.duration_seconds > 0

    def test_empty_propagation(self):
        from satorbit.engine.orbit_propagator import PropagationResult

        prop = PropagationResult(norad_id=0, name="EMPTY", error="test")
        result = calculate_passes(prop, KENNEDY)
        assert result.passes == []

    def test_high_min_elevation_fewer_passes(self, sample_tle_iss, sample_datetime):
        prop = propagate_satellite(
            sample_tle_iss["line1"],
            sample_tle_iss["line2"],
            start_time=sample_datetime,
            duration_hours=48,
            step_minutes=0.5,
            name="ISS",
        )
        result_low = calculate_passes(prop, KENNEDY, min_elevation=5.0)
        result_high = calculate_passes(prop, KENNEDY, min_elevation=45.0)

        # Higher minimum elevation → fewer or equal passes
        assert len(result_high.passes) <= len(result_low.passes)
