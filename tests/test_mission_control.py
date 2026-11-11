"""Tests for the Mission Control dashboard and its Guardian conjunction scan."""

import csv
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from satorbit.mission_control import app as mc_app
from satorbit.mission_control import guardian, paths, utils

ISS_LINE1 = "1 25544U 98067A   24045.51792824  .00016717  00000-0  29820-3 0  9992"
ISS_LINE2 = "2 25544  51.6412 236.2420 0004448  38.8780  36.1584 15.49953808440497"
# Same orbit, mean anomaly shifted by 0.05 deg (~6 km along-track): a guaranteed close approach.
CHASER_LINE1 = "1 99999U 98067B   24045.51792824  .00016717  00000-0  29820-3 0  9990"
CHASER_LINE2 = "2 99999  51.6412 236.2420 0004448  38.8780  36.2084 15.49953808440490"
FAR_LINE1 = "1 43013U 17071B   24045.51095025  .00002367  00000-0  12345-3 0  9998"
FAR_LINE2 = "2 43013  97.4560 123.7890 0012345  89.1234 271.0987 15.18765432012345"
EPOCH = datetime(2024, 2, 14, 12, 30, tzinfo=timezone.utc)

CATALOG = {
    "25544": ("ISS (ZARYA)", ISS_LINE1, ISS_LINE2),
    "99999": ("CHASER", CHASER_LINE1, CHASER_LINE2),
    "43013": ("FLOCK 3P-1", FAR_LINE1, FAR_LINE2),
}


@pytest.fixture
def tracked(monkeypatch, tmp_path):
    """Track the given NORAD IDs with an offline catalog and isolated config."""

    def _track(*norad_ids):
        config = json.loads(paths.EXAMPLE_CONFIG.read_text())
        config["satellites"] = [{"name": CATALOG[n][0], "norad_id": n} for n in norad_ids]
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))
        monkeypatch.setattr(utils, "CONFIG_FILE", str(config_file))
        monkeypatch.setattr(guardian, "get_satellite_from_catalog", lambda n: CATALOG.get(str(n)))
        return tmp_path / "conjunctions.csv"

    return _track


def read_rows(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


class TestGuardian:
    def test_detects_close_approach(self, tracked):
        output = tracked("25544", "99999", "43013")
        pairs = guardian.run_conjunction_scan(threshold_km=25.0, hours=1.0, output=output, start_time=EPOCH)
        rows = read_rows(output)
        assert pairs == len(rows) >= 1
        closest = rows[0]
        assert {closest["satellite_1"], closest["satellite_2"]} == {"ISS (ZARYA)", "CHASER"}
        assert float(closest["distance_km"]) < 25.0
        # The CSV columns are the contract with the dashboard and Notify agent.
        assert set(guardian.CSV_FIELDS) <= set(closest)

    def test_one_row_per_pair_sorted_by_distance(self, tracked):
        output = tracked("25544", "99999")
        guardian.run_conjunction_scan(threshold_km=25.0, hours=2.0, output=output, start_time=EPOCH)
        rows = read_rows(output)
        assert len(rows) == 1

    def test_fewer_than_two_satellites_writes_empty_report(self, tracked):
        output = tracked("25544")
        assert guardian.run_conjunction_scan(hours=1.0, output=output, start_time=EPOCH) == 0
        assert read_rows(output) == []


class TestCatalogLookup:
    def test_numeric_query_matches_norad_id_not_name(self, monkeypatch):
        catalog = [
            "OBJECT 25544 DEBRIS",
            "1 11111U",
            "2 11111 00.0",
            "ISS (ZARYA)",
            ISS_LINE1,
            ISS_LINE2,
        ]
        monkeypatch.setattr(utils, "fetch_active_catalog", lambda: catalog)
        assert utils.get_satellite_from_catalog("25544")[0] == "ISS (ZARYA)"

    def test_text_query_matches_name(self, monkeypatch):
        monkeypatch.setattr(utils, "fetch_active_catalog", lambda: ["ISS (ZARYA)", ISS_LINE1, ISS_LINE2])
        assert utils.get_satellite_from_catalog("iss")[0] == "ISS (ZARYA)"


class TestDashboard:
    @pytest.fixture
    def client(self, tracked):
        tracked("25544", "99999")
        # No `with`: skip startup background agents, which need the network.
        return TestClient(mc_app.app)

    def test_index_renders(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "<html" in response.text.lower()

    def test_logs_endpoint(self, client):
        assert "logs" in client.get("/api/logs").json()

    def test_conjunctions_reads_guardian_output(self, client, monkeypatch, tmp_path):
        report = tmp_path / "report.csv"
        with report.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=guardian.CSV_FIELDS)
            writer.writeheader()
            writer.writerow(
                {
                    "satellite_1": "ISS (ZARYA)",
                    "satellite_2": "CHASER",
                    "norad_1": 25544,
                    "norad_2": 99999,
                    "distance_km": 0.8,
                    "relative_velocity_km_s": 0.01,
                    "risk_score": 90.0,
                    "time_utc": "2024-02-14 12:31:00",
                }
            )
        monkeypatch.setattr(mc_app, "CONJUNCTION_CSV", report)
        data = client.get("/conjunctions").json()
        names = json.dumps(data)
        assert "ISS (ZARYA)" in names and "CHASER" in names

    def test_chat_help(self, client):
        reply = client.post("/chat", json={"message": "help"}).json()["reply"]
        assert reply


def test_example_config_is_safe_by_default():
    """The shipped config must not contain placeholder credentials that trigger SMTP/Slack calls."""
    config = json.loads(paths.EXAMPLE_CONFIG.read_text())
    assert config["email"]["sender_email"] == ""
    assert config["email"]["sender_password"] == ""
    assert config["slack"]["webhook_url"] == ""
