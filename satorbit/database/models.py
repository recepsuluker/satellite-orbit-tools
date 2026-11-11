"""SQLite database models and schema definitions."""

from __future__ import annotations

import sqlite3

from satorbit.config import get_settings
from satorbit.logging_config import get_logger

logger = get_logger("database.models")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS satellites (
    norad_id        INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    intl_designator TEXT,
    tle_line1       TEXT NOT NULL,
    tle_line2       TEXT NOT NULL,
    epoch           TEXT,
    inclination     REAL,
    eccentricity    REAL,
    period_min      REAL,
    apogee_km       REAL,
    perigee_km      REAL,
    object_type     TEXT DEFAULT 'PAYLOAD',
    country_code    TEXT,
    launch_date     TEXT,
    decay_date      TEXT,
    rcs_size        TEXT,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS conjunction_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at     TEXT NOT NULL DEFAULT (datetime('now')),
    event_time      TEXT NOT NULL,
    satellite_a_id  INTEGER NOT NULL,
    satellite_b_id  INTEGER NOT NULL,
    distance_km     REAL NOT NULL,
    relative_vel    REAL,
    risk_score      REAL,
    lat_a           REAL,
    lon_a           REAL,
    alt_a           REAL,
    lat_b           REAL,
    lon_b           REAL,
    alt_b           REAL,
    FOREIGN KEY (satellite_a_id) REFERENCES satellites(norad_id),
    FOREIGN KEY (satellite_b_id) REFERENCES satellites(norad_id)
);

CREATE TABLE IF NOT EXISTS ground_stations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    elevation_m     REAL DEFAULT 0,
    description     TEXT
);

CREATE TABLE IF NOT EXISTS pass_predictions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id      INTEGER NOT NULL,
    norad_id        INTEGER NOT NULL,
    aos_time        TEXT NOT NULL,
    aos_azimuth     REAL,
    max_time        TEXT,
    max_elevation   REAL,
    max_azimuth     REAL,
    los_time        TEXT NOT NULL,
    los_azimuth     REAL,
    duration_sec    REAL,
    computed_at     TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (station_id) REFERENCES ground_stations(id),
    FOREIGN KEY (norad_id) REFERENCES satellites(norad_id)
);

CREATE TABLE IF NOT EXISTS catalog_sync_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_time       TEXT NOT NULL DEFAULT (datetime('now')),
    satellites_added INTEGER DEFAULT 0,
    satellites_updated INTEGER DEFAULT 0,
    total_in_catalog INTEGER DEFAULT 0,
    source          TEXT DEFAULT 'space-track',
    status          TEXT DEFAULT 'success',
    error_message   TEXT
);

CREATE INDEX IF NOT EXISTS idx_satellites_name ON satellites(name);
CREATE INDEX IF NOT EXISTS idx_satellites_object_type ON satellites(object_type);
CREATE INDEX IF NOT EXISTS idx_conjunction_event_time ON conjunction_events(event_time);
CREATE INDEX IF NOT EXISTS idx_conjunction_risk ON conjunction_events(risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_pass_station ON pass_predictions(station_id, aos_time);
"""

DEFAULT_STATIONS = [
    ("Kennedy Space Center", 28.5721, -80.6480, 3.0, "NASA Kennedy Space Center, Florida"),
    ("Baikonur Cosmodrome", 45.9650, 63.3050, 90.0, "Baikonur Cosmodrome, Kazakhstan"),
    ("ESA Kourou", 5.2360, -52.7690, 15.0, "Guiana Space Centre, French Guiana"),
    ("ISRO Sriharikota", 13.7199, 80.2304, 5.0, "Satish Dhawan Space Centre, India"),
    ("Vandenberg SFB", 34.7420, -120.5724, 112.0, "Vandenberg Space Force Base, California"),
]


def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with WAL mode for better concurrency."""
    settings = get_settings()
    db_path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def initialize_database() -> None:
    """Create all tables and seed default data."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)

        # Seed default ground stations
        for name, lat, lon, elev, desc in DEFAULT_STATIONS:
            conn.execute(
                "INSERT OR IGNORE INTO ground_stations (name, latitude, longitude, elevation_m, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, lat, lon, elev, desc),
            )
        conn.commit()
        logger.info("Database initialized at %s", get_settings().db_path)
    except Exception as e:
        logger.error("Database initialization failed: %s", e)
        raise
    finally:
        conn.close()
