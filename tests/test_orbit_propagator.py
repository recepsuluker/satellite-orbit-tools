"""Tests for the orbit propagation engine."""

from satorbit.engine.orbit_propagator import (
    PropagationResult,
    SatellitePosition,
    propagate_batch,
    propagate_satellite,
    tle_to_satrec,
)


class TestTleToSatrec:
    def test_valid_tle(self, sample_tle_iss):
        sat = tle_to_satrec(sample_tle_iss["line1"], sample_tle_iss["line2"])
        assert sat is not None
        assert sat.satnum == 25544

    def test_invalid_tle_returns_nonstandard(self):
        # SGP4 may not raise but produces a satrec with error flags
        sat = tle_to_satrec(
            "1 00000U 00000A   00001.00000000  .00000000  00000-0  00000-0 0    09",
            "2 00000   0.0000   0.0000 0000000   0.0000   0.0000  1.00000000    06",
        )
        assert sat is not None


class TestPropagateSatellite:
    def test_basic_propagation(self, sample_tle_iss, sample_datetime):
        result = propagate_satellite(
            sample_tle_iss["line1"],
            sample_tle_iss["line2"],
            start_time=sample_datetime,
            duration_hours=1.0,
            step_minutes=10.0,
            name="ISS",
        )
        assert isinstance(result, PropagationResult)
        assert result.name == "ISS"
        assert result.error is None
        assert len(result.positions) == 7  # 0, 10, 20, 30, 40, 50, 60 min

    def test_position_has_geodetic_coords(self, sample_tle_iss, sample_datetime):
        result = propagate_satellite(
            sample_tle_iss["line1"],
            sample_tle_iss["line2"],
            start_time=sample_datetime,
            duration_hours=0.1,
            step_minutes=1.0,
            name="ISS",
        )
        pos = result.positions[0]
        assert isinstance(pos, SatellitePosition)
        assert -90 <= pos.latitude <= 90
        assert -180 <= pos.longitude <= 180
        assert pos.altitude_km > 200  # ISS altitude
        assert pos.altitude_km < 600

    def test_position_has_eci_vectors(self, sample_tle_iss, sample_datetime):
        result = propagate_satellite(
            sample_tle_iss["line1"],
            sample_tle_iss["line2"],
            start_time=sample_datetime,
            duration_hours=0.1,
            step_minutes=1.0,
            name="ISS",
        )
        pos = result.positions[0]
        # ECI position should be roughly at LEO distance
        r = (pos.x_km**2 + pos.y_km**2 + pos.z_km**2) ** 0.5
        assert 6500 < r < 7000  # ~6371 + altitude

    def test_invalid_tle_returns_no_positions(self):
        # SGP4 with bad data may not raise but will produce 0 valid positions
        result = propagate_satellite("bad", "data", name="BROKEN")
        # Either error is set or no valid positions were produced
        assert result.error is not None or len(result.positions) == 0

    def test_zero_duration(self, sample_tle_iss, sample_datetime):
        result = propagate_satellite(
            sample_tle_iss["line1"],
            sample_tle_iss["line2"],
            start_time=sample_datetime,
            duration_hours=0.0,
            step_minutes=1.0,
            name="ISS",
        )
        assert len(result.positions) == 1  # Only t=0

    def test_default_start_time(self, sample_tle_iss):
        result = propagate_satellite(
            sample_tle_iss["line1"],
            sample_tle_iss["line2"],
            duration_hours=0.1,
            step_minutes=1.0,
            name="ISS",
        )
        # Should use current time — at least positions should exist
        assert len(result.positions) > 0


class TestPropagateBatch:
    def test_batch_propagation(self, sample_tle_iss, sample_tle_starlink, sample_datetime):
        satellites = [
            ("ISS", sample_tle_iss["line1"], sample_tle_iss["line2"]),
            ("STARLINK", sample_tle_starlink["line1"], sample_tle_starlink["line2"]),
        ]
        results = propagate_batch(satellites, start_time=sample_datetime, duration_hours=0.5, step_minutes=5)
        assert len(results) == 2
        assert results[0].name == "ISS"
        assert results[1].name == "STARLINK"
        assert all(r.error is None for r in results)
