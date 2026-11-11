"""Shared test fixtures for satellite-orbit-tools."""

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Keep all application data (DB, logs, Mission Control config) in a temp dir
os.environ["SATORBIT_HOME"] = tempfile.mkdtemp(prefix="satorbit_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mktemp(suffix='.db')}"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["LOG_DIR"] = tempfile.mkdtemp()


# ── Sample TLE Data ──────────────────────────────────────────────

SAMPLE_TLE_ISS = {
    "name": "ISS (ZARYA)",
    "norad_id": 25544,
    "line1": "1 25544U 98067A   24045.51792824  .00016717  00000-0  29820-3 0  9992",
    "line2": "2 25544  51.6412 236.2420 0004448  38.8780  36.1584 15.49953808440497",
}

SAMPLE_TLE_STARLINK = {
    "name": "STARLINK-1007",
    "norad_id": 44713,
    "line1": "1 44713U 19074A   24045.54326621  .00001584  00000-0  11834-3 0  9999",
    "line2": "2 44713  53.0541 242.9636 0001406  85.4385 274.6779 15.06388506244765",
}

SAMPLE_TLE_FLOCK = {
    "name": "FLOCK 3P-1",
    "norad_id": 43013,
    "line1": "1 43013U 17071B   24045.51095025  .00002367  00000-0  12345-3 0  9998",
    "line2": "2 43013  97.4560 123.7890 0012345  89.1234 271.0987 15.18765432012345",
}


@pytest.fixture
def sample_tle_iss():
    return SAMPLE_TLE_ISS


@pytest.fixture
def sample_tle_starlink():
    return SAMPLE_TLE_STARLINK


@pytest.fixture
def sample_tle_flock():
    return SAMPLE_TLE_FLOCK


@pytest.fixture
def initialized_db():
    """Initialize a fresh test database."""
    from satorbit.database.models import initialize_database

    initialize_database()
    from satorbit.database.manager import SatelliteDB

    return SatelliteDB


@pytest.fixture
def sample_datetime():
    return datetime(2024, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
