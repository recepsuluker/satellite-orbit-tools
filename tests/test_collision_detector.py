"""Tests for the collision detection engine."""

from datetime import datetime, timezone

from satorbit.engine.collision_detector import (
    CollisionAnalysis,
    ConjunctionEvent,
    _calculate_risk_score,
    _distance_3d,
    _relative_velocity,
    analyze_collisions,
    check_conjunction_pair,
)
from satorbit.engine.orbit_propagator import PropagationResult, SatellitePosition, propagate_satellite


class TestDistance3D:
    def test_same_point(self):
        p1 = SatellitePosition(
            timestamp=datetime.now(timezone.utc),
            latitude=0,
            longitude=0,
            altitude_km=400,
            x_km=6771,
            y_km=0,
            z_km=0,
        )
        assert _distance_3d(p1, p1) == 0.0

    def test_known_distance(self):
        t = datetime.now(timezone.utc)
        p1 = SatellitePosition(timestamp=t, latitude=0, longitude=0, altitude_km=0, x_km=0, y_km=0, z_km=0)
        p2 = SatellitePosition(timestamp=t, latitude=0, longitude=0, altitude_km=0, x_km=3, y_km=4, z_km=0)
        assert abs(_distance_3d(p1, p2) - 5.0) < 1e-10

    def test_3d_distance(self):
        t = datetime.now(timezone.utc)
        p1 = SatellitePosition(timestamp=t, latitude=0, longitude=0, altitude_km=0, x_km=1, y_km=2, z_km=3)
        p2 = SatellitePosition(timestamp=t, latitude=0, longitude=0, altitude_km=0, x_km=4, y_km=6, z_km=3)
        expected = (9 + 16 + 0) ** 0.5  # 5.0
        assert abs(_distance_3d(p1, p2) - expected) < 1e-10


class TestRelativeVelocity:
    def test_same_velocity(self):
        t = datetime.now(timezone.utc)
        p1 = SatellitePosition(
            timestamp=t, latitude=0, longitude=0, altitude_km=0, vx_km_s=7.5, vy_km_s=0, vz_km_s=0
        )
        p2 = SatellitePosition(
            timestamp=t, latitude=0, longitude=0, altitude_km=0, vx_km_s=7.5, vy_km_s=0, vz_km_s=0
        )
        assert _relative_velocity(p1, p2) == 0.0

    def test_opposing_velocities(self):
        t = datetime.now(timezone.utc)
        p1 = SatellitePosition(
            timestamp=t, latitude=0, longitude=0, altitude_km=0, vx_km_s=7.5, vy_km_s=0, vz_km_s=0
        )
        p2 = SatellitePosition(
            timestamp=t, latitude=0, longitude=0, altitude_km=0, vx_km_s=-7.5, vy_km_s=0, vz_km_s=0
        )
        assert abs(_relative_velocity(p1, p2) - 15.0) < 1e-10


class TestRiskScore:
    def test_zero_distance_max_risk(self):
        score = _calculate_risk_score(0.0, 10.0)
        assert score >= 90

    def test_large_distance_low_risk(self):
        score = _calculate_risk_score(50.0, 5.0)
        assert score < 5

    def test_moderate_distance(self):
        score = _calculate_risk_score(2.0, 7.0)
        assert 10 < score < 80

    def test_risk_increases_with_velocity(self):
        score_low_v = _calculate_risk_score(1.0, 1.0)
        score_high_v = _calculate_risk_score(1.0, 14.0)
        assert score_high_v > score_low_v


class TestCheckConjunctionPair:
    def test_with_real_tle(self, sample_tle_iss, sample_tle_starlink, sample_datetime):
        prop_a = propagate_satellite(
            sample_tle_iss["line1"],
            sample_tle_iss["line2"],
            start_time=sample_datetime,
            duration_hours=2,
            step_minutes=1,
            name="ISS",
        )
        prop_b = propagate_satellite(
            sample_tle_starlink["line1"],
            sample_tle_starlink["line2"],
            start_time=sample_datetime,
            duration_hours=2,
            step_minutes=1,
            name="STARLINK",
        )
        # These satellites are in different orbits — unlikely to have conjunction at 10km
        events = check_conjunction_pair(prop_a, prop_b, threshold_km=10.0)
        assert isinstance(events, list)
        # Events could be 0 or more, just check the structure
        for e in events:
            assert isinstance(e, ConjunctionEvent)
            assert e.distance_km < 10.0

    def test_with_error_result(self, sample_tle_iss, sample_datetime):
        prop_a = propagate_satellite(
            sample_tle_iss["line1"],
            sample_tle_iss["line2"],
            start_time=sample_datetime,
            duration_hours=1,
            step_minutes=1,
            name="ISS",
        )
        prop_b = PropagationResult(norad_id=0, name="BROKEN", error="test error")
        events = check_conjunction_pair(prop_a, prop_b)
        assert events == []


class TestAnalyzeCollisions:
    def test_basic_analysis(self, sample_tle_iss, sample_tle_starlink, sample_datetime):
        prop_a = propagate_satellite(
            sample_tle_iss["line1"],
            sample_tle_iss["line2"],
            start_time=sample_datetime,
            duration_hours=1,
            step_minutes=5,
            name="ISS",
        )
        prop_b = propagate_satellite(
            sample_tle_starlink["line1"],
            sample_tle_starlink["line2"],
            start_time=sample_datetime,
            duration_hours=1,
            step_minutes=5,
            name="STARLINK",
        )
        analysis = analyze_collisions([prop_a, prop_b], threshold_km=10.0)

        assert isinstance(analysis, CollisionAnalysis)
        assert analysis.total_pairs_checked == 1
        assert analysis.threshold_km == 10.0
        assert analysis.analysis_duration_sec >= 0

    def test_single_satellite_no_pairs(self, sample_tle_iss, sample_datetime):
        prop = propagate_satellite(
            sample_tle_iss["line1"],
            sample_tle_iss["line2"],
            start_time=sample_datetime,
            duration_hours=1,
            step_minutes=5,
            name="ISS",
        )
        analysis = analyze_collisions([prop])
        assert analysis.total_pairs_checked == 0
        assert analysis.total_conjunctions == 0

    def test_empty_list(self):
        analysis = analyze_collisions([])
        assert analysis.total_pairs_checked == 0
