"""Tests for export utilities."""

from datetime import datetime, timezone

import pytest

from satorbit.engine.collision_detector import CollisionAnalysis, ConjunctionEvent
from satorbit.engine.visibility_calculator import GroundStation, PassEvent, VisibilityResult
from satorbit.utils.export import conjunction_events_to_csv, generate_html_report, passes_to_csv


@pytest.fixture
def sample_analysis():
    events = [
        ConjunctionEvent(
            time=datetime(2024, 2, 15, 12, 0, 0, tzinfo=timezone.utc),
            satellite_a="ISS",
            satellite_b="STARLINK-1007",
            norad_id_a=25544,
            norad_id_b=44713,
            distance_km=5.234,
            relative_velocity_km_s=12.5,
            risk_score=85.0,
            pos_a=(28.5, -80.6, 408.0),
            pos_b=(28.6, -80.5, 550.0),
        ),
        ConjunctionEvent(
            time=datetime(2024, 2, 15, 14, 30, 0, tzinfo=timezone.utc),
            satellite_a="ISS",
            satellite_b="FLOCK-3P",
            norad_id_a=25544,
            norad_id_b=43013,
            distance_km=8.123,
            relative_velocity_km_s=3.2,
            risk_score=15.0,
            pos_a=(30.0, -75.0, 410.0),
            pos_b=(30.1, -74.9, 500.0),
        ),
    ]
    return CollisionAnalysis(
        total_pairs_checked=3,
        total_conjunctions=2,
        threshold_km=10.0,
        analysis_duration_sec=1.5,
        events=events,
        high_risk_count=1,
        medium_risk_count=0,
        low_risk_count=1,
    )


@pytest.fixture
def sample_visibility():
    return VisibilityResult(
        station=GroundStation("Kennedy", 28.5721, -80.648, 3.0),
        satellite_name="ISS",
        passes=[
            PassEvent(
                satellite_name="ISS",
                norad_id=25544,
                aos_time=datetime(2024, 2, 15, 5, 0, 0, tzinfo=timezone.utc),
                aos_azimuth=220.0,
                max_time=datetime(2024, 2, 15, 5, 5, 0, tzinfo=timezone.utc),
                max_elevation=45.0,
                max_azimuth=180.0,
                los_time=datetime(2024, 2, 15, 5, 10, 0, tzinfo=timezone.utc),
                los_azimuth=130.0,
                duration_seconds=600.0,
                max_distance_km=800.0,
            ),
        ],
        analysis_window_hours=24.0,
    )


class TestConjunctionCSV:
    def test_csv_generation(self, sample_analysis):
        csv = conjunction_events_to_csv(sample_analysis)
        assert "ISS" in csv
        assert "STARLINK-1007" in csv
        assert "5.2340" in csv
        lines = csv.strip().split("\n")
        assert len(lines) == 3  # header + 2 events

    def test_empty_analysis(self):
        analysis = CollisionAnalysis()
        csv = conjunction_events_to_csv(analysis)
        lines = csv.strip().split("\n")
        assert len(lines) == 1  # header only


class TestPassesCSV:
    def test_csv_generation(self, sample_visibility):
        csv = passes_to_csv(sample_visibility)
        assert "ISS" in csv
        assert "25544" in csv
        lines = csv.strip().split("\n")
        assert len(lines) == 2  # header + 1 pass


class TestHTMLReport:
    def test_html_generation(self, sample_analysis):
        html = generate_html_report(sample_analysis)
        assert "<!DOCTYPE html>" in html
        assert "Collision Analysis Report" in html
        assert "ISS" in html
        assert "HIGH" in html
        assert "85" in html

    def test_empty_report(self):
        analysis = CollisionAnalysis()
        html = generate_html_report(analysis)
        assert "No conjunction events detected" in html
