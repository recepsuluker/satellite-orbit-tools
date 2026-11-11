"""Tests for the FastAPI backend."""

import pytest
from fastapi.testclient import TestClient

from satorbit.api.main import app
from satorbit.database.manager import SatelliteDB
from satorbit.database.models import initialize_database


@pytest.fixture(autouse=True)
def setup_db():
    initialize_database()
    # Seed a test satellite
    with SatelliteDB() as db:
        db.upsert_satellite(
            {
                "norad_id": 25544,
                "name": "ISS (ZARYA)",
                "tle_line1": "1 25544U 98067A   24045.51792824  .00016717  00000-0  29820-3 0  9992",
                "tle_line2": "2 25544  51.6412 236.2420 0004448  38.8780  36.1584 15.49953808440497",
                "object_type": "PAYLOAD",
            }
        )
        db.upsert_satellite(
            {
                "norad_id": 44713,
                "name": "STARLINK-1007",
                "tle_line1": "1 44713U 19074A   24045.54326621  .00001584  00000-0  11834-3 0  9999",
                "tle_line2": "2 44713  53.0541 242.9636 0001406  85.4385 274.6779 15.06388506244765",
                "object_type": "PAYLOAD",
            }
        )
        db.conn.commit()
    yield


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoints:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "operational"
        assert "version" in data

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "satellites_in_catalog" in data


class TestSatelliteEndpoints:
    def test_list_satellites(self, client):
        resp = client.get("/api/v1/satellites/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_satellite(self, client):
        resp = client.get("/api/v1/satellites/25544")
        assert resp.status_code == 200
        data = resp.json()
        assert data["norad_id"] == 25544
        assert data["name"] == "ISS (ZARYA)"

    def test_get_nonexistent_satellite(self, client):
        resp = client.get("/api/v1/satellites/99999999")
        assert resp.status_code == 404

    def test_search_satellites(self, client):
        resp = client.get("/api/v1/satellites/?query=ISS")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_catalog_stats(self, client):
        resp = client.get("/api/v1/satellites/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2

    def test_satellite_position(self, client):
        resp = client.get("/api/v1/satellites/25544/position?duration_hours=0.1&step_minutes=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["norad_id"] == 25544
        assert data["position_count"] > 0
        assert len(data["positions"]) > 0
        pos = data["positions"][0]
        assert "lat" in pos
        assert "lon" in pos
        assert "alt_km" in pos


class TestCollisionEndpoints:
    def test_analyze_collision(self, client):
        resp = client.post(
            "/api/v1/collision/analyze",
            json={
                "norad_ids": [25544, 44713],
                "threshold_km": 10.0,
                "duration_hours": 1.0,
                "step_minutes": 5.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_pairs_checked" in data
        assert data["total_pairs_checked"] == 1

    def test_analyze_too_few_satellites(self, client):
        resp = client.post(
            "/api/v1/collision/analyze",
            json={
                "norad_ids": [25544],
            },
        )
        assert resp.status_code == 400

    def test_collision_history(self, client):
        resp = client.get("/api/v1/collision/history")
        assert resp.status_code == 200
        assert "events" in resp.json()

    def test_quick_check(self, client):
        resp = client.post("/api/v1/collision/quick-check?norad_id_a=25544&norad_id_b=44713&duration_hours=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["satellite_a"] == "ISS (ZARYA)"
        assert data["satellite_b"] == "STARLINK-1007"


class TestVisibilityEndpoints:
    def test_predict_passes(self, client):
        resp = client.get("/api/v1/visibility/passes/25544?duration_hours=6")
        assert resp.status_code == 200
        data = resp.json()
        assert data["norad_id"] == 25544
        assert "passes" in data

    def test_list_stations(self, client):
        resp = client.get("/api/v1/visibility/stations")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["stations"]) >= 5
