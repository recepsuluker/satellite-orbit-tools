"""Tests for CelesTrak client and demo data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from satorbit.utils.celestrak_client import GROUPS, _parse_tle_text, get_demo_satellites


class TestDemoSatellites:
    def test_demo_returns_satellites(self):
        sats = get_demo_satellites()
        assert len(sats) > 0

    def test_demo_has_iss(self):
        sats = get_demo_satellites()
        names = [s["name"] for s in sats]
        assert "ISS (ZARYA)" in names

    def test_demo_satellite_fields(self):
        sats = get_demo_satellites()
        required = [
            "norad_id",
            "name",
            "tle_line1",
            "tle_line2",
            "epoch",
            "inclination",
            "eccentricity",
            "period_min",
            "apogee_km",
            "perigee_km",
        ]
        for sat in sats:
            for field in required:
                assert field in sat, f"Missing field '{field}' in {sat['name']}"

    def test_demo_norad_ids_unique(self):
        sats = get_demo_satellites()
        ids = [s["norad_id"] for s in sats]
        assert len(ids) == len(set(ids))

    def test_demo_tle_lines_valid(self):
        sats = get_demo_satellites()
        for sat in sats:
            assert sat["tle_line1"].startswith("1 ")
            assert sat["tle_line2"].startswith("2 ")

    def test_demo_orbital_params_reasonable(self):
        sats = get_demo_satellites()
        for sat in sats:
            assert 0 <= sat["inclination"] <= 180
            assert 0 <= sat["eccentricity"] < 1
            assert sat["period_min"] > 0


class TestParseHelpers:
    def test_parse_tle_text_three_line(self):
        text = """ISS (ZARYA)
1 25544U 98067A   24045.51792824  .00016717  00000-0  29820-3 0  9992
2 25544  51.6412 236.2420 0004448  38.8780  36.1584 15.49953808440497"""
        results = _parse_tle_text(text)
        assert len(results) == 1
        assert results[0]["norad_id"] == 25544

    def test_parse_tle_text_empty(self):
        assert _parse_tle_text("") == []
        assert _parse_tle_text("   \n\n  ") == []


class TestGroups:
    def test_groups_dict_not_empty(self):
        assert len(GROUPS) > 0

    def test_stations_in_groups(self):
        assert "stations" in GROUPS
        assert "active" in GROUPS
