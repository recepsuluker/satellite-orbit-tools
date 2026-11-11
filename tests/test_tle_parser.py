"""Tests for TLE parsing utilities."""

from datetime import timezone

from satorbit.utils.tle_parser import TLEData, parse_tle, parse_tle_text

SAMPLE_NAME = "ISS (ZARYA)"
SAMPLE_LINE1 = "1 25544U 98067A   24045.51792824  .00016717  00000-0  29820-3 0  9992"
SAMPLE_LINE2 = "2 25544  51.6412 236.2420 0004448  38.8780  36.1584 15.49953808440497"


class TestParseTle:
    def test_basic_parsing(self):
        result = parse_tle(SAMPLE_NAME, SAMPLE_LINE1, SAMPLE_LINE2)
        assert isinstance(result, TLEData)
        assert result.name == "ISS (ZARYA)"
        assert result.norad_id == 25544
        assert result.intl_designator == "98067A"

    def test_orbital_elements(self):
        result = parse_tle(SAMPLE_NAME, SAMPLE_LINE1, SAMPLE_LINE2)
        assert abs(result.inclination - 51.6412) < 0.001
        assert abs(result.eccentricity - 0.0004448) < 0.0000001
        assert result.mean_motion > 15.0

    def test_derived_values(self):
        result = parse_tle(SAMPLE_NAME, SAMPLE_LINE1, SAMPLE_LINE2)
        assert result.period_min > 90  # ~92 min for ISS
        assert result.period_min < 95
        assert result.apogee_km > 400
        assert result.perigee_km > 400

    def test_epoch(self):
        result = parse_tle(SAMPLE_NAME, SAMPLE_LINE1, SAMPLE_LINE2)
        assert result.epoch.year == 2024
        assert result.epoch.tzinfo == timezone.utc


class TestParseTleText:
    def test_three_line_format(self):
        text = f"{SAMPLE_NAME}\n{SAMPLE_LINE1}\n{SAMPLE_LINE2}"
        results = parse_tle_text(text)
        assert len(results) == 1
        assert results[0].norad_id == 25544

    def test_multiple_satellites(self):
        text = f"""ISS (ZARYA)
{SAMPLE_LINE1}
{SAMPLE_LINE2}
STARLINK-1007
1 44713U 19074A   24045.54326621  .00001584  00000-0  11834-3 0  9999
2 44713  53.0541 242.9636 0001406  85.4385 274.6779 15.06388506244765"""
        results = parse_tle_text(text)
        assert len(results) == 2

    def test_two_line_format(self):
        text = f"{SAMPLE_LINE1}\n{SAMPLE_LINE2}"
        results = parse_tle_text(text)
        assert len(results) == 1

    def test_empty_input(self):
        assert parse_tle_text("") == []
        assert parse_tle_text("   \n  \n  ") == []
