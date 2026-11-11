"""Database operations manager for satellite catalog and analysis results."""

from __future__ import annotations

from typing import Any

from satorbit.database.models import get_connection
from satorbit.logging_config import get_logger

logger = get_logger("database.manager")


class SatelliteDB:
    """High-level database operations for the satellite catalog."""

    def __init__(self):
        self.conn = get_connection()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ── Satellite CRUD ──────────────────────────────────────────

    def upsert_satellite(self, sat: dict) -> None:
        """Insert or update a satellite record."""
        self.conn.execute(
            """INSERT INTO satellites
               (norad_id, name, intl_designator, tle_line1, tle_line2,
                epoch, inclination, eccentricity, period_min, apogee_km, perigee_km,
                object_type, country_code, launch_date, decay_date, rcs_size, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(norad_id) DO UPDATE SET
                name=excluded.name, tle_line1=excluded.tle_line1, tle_line2=excluded.tle_line2,
                epoch=excluded.epoch, inclination=excluded.inclination,
                eccentricity=excluded.eccentricity, period_min=excluded.period_min,
                apogee_km=excluded.apogee_km, perigee_km=excluded.perigee_km,
                object_type=excluded.object_type, updated_at=datetime('now')
            """,
            (
                sat["norad_id"],
                sat.get("name", "UNKNOWN"),
                sat.get("intl_designator"),
                sat["tle_line1"],
                sat["tle_line2"],
                sat.get("epoch"),
                sat.get("inclination"),
                sat.get("eccentricity"),
                sat.get("period_min"),
                sat.get("apogee_km"),
                sat.get("perigee_km"),
                sat.get("object_type", "PAYLOAD"),
                sat.get("country_code"),
                sat.get("launch_date"),
                sat.get("decay_date"),
                sat.get("rcs_size"),
            ),
        )

    def upsert_satellites_batch(self, satellites: list[dict]) -> tuple[int, int]:
        """Batch upsert satellites. Returns (added, updated) counts."""
        added = updated = 0
        for sat in satellites:
            existing = self.get_satellite(sat["norad_id"])
            self.upsert_satellite(sat)
            if existing:
                updated += 1
            else:
                added += 1
        self.conn.commit()
        return added, updated

    def get_satellite(self, norad_id: int) -> dict | None:
        """Get a satellite by NORAD ID."""
        row = self.conn.execute("SELECT * FROM satellites WHERE norad_id = ?", (norad_id,)).fetchone()
        return dict(row) if row else None

    def search_satellites(
        self,
        query: str = "",
        object_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Search satellites by name or NORAD ID."""
        conditions = []
        params: list[Any] = []

        if query:
            conditions.append("(name LIKE ? OR CAST(norad_id AS TEXT) LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        if object_type:
            conditions.append("object_type = ?")
            params.append(object_type)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"SELECT * FROM satellites {where} ORDER BY name LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_satellite_count(self, object_type: str | None = None) -> int:
        """Get total satellite count, optionally filtered by type."""
        if object_type:
            row = self.conn.execute(
                "SELECT COUNT(*) as cnt FROM satellites WHERE object_type = ?",
                (object_type,),
            ).fetchone()
        else:
            row = self.conn.execute("SELECT COUNT(*) as cnt FROM satellites").fetchone()
        return row["cnt"] if row else 0

    def get_object_type_stats(self) -> list[dict]:
        """Get satellite count by object type."""
        rows = self.conn.execute(
            "SELECT object_type, COUNT(*) as count FROM satellites GROUP BY object_type ORDER BY count DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Conjunction Events ──────────────────────────────────────

    def save_conjunction_event(self, event: dict) -> int:
        """Save a conjunction event and return its ID."""
        cursor = self.conn.execute(
            """INSERT INTO conjunction_events
               (event_time, satellite_a_id, satellite_b_id, distance_km,
                relative_vel, risk_score, lat_a, lon_a, alt_a, lat_b, lon_b, alt_b)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event["event_time"],
                event["satellite_a_id"],
                event["satellite_b_id"],
                event["distance_km"],
                event.get("relative_vel"),
                event.get("risk_score"),
                event.get("lat_a"),
                event.get("lon_a"),
                event.get("alt_a"),
                event.get("lat_b"),
                event.get("lon_b"),
                event.get("alt_b"),
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_recent_conjunctions(self, limit: int = 50) -> list[dict]:
        """Get recent conjunction events ordered by risk score."""
        rows = self.conn.execute(
            """SELECT ce.*, sa.name as sat_a_name, sb.name as sat_b_name
               FROM conjunction_events ce
               LEFT JOIN satellites sa ON ce.satellite_a_id = sa.norad_id
               LEFT JOIN satellites sb ON ce.satellite_b_id = sb.norad_id
               ORDER BY ce.risk_score DESC, ce.detected_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Ground Stations ─────────────────────────────────────────

    def get_ground_stations(self) -> list[dict]:
        """Get all ground stations."""
        rows = self.conn.execute("SELECT * FROM ground_stations ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def add_ground_station(self, name: str, lat: float, lon: float, elev: float = 0, desc: str = "") -> int:
        """Add a ground station."""
        cursor = self.conn.execute(
            "INSERT INTO ground_stations (name, latitude, longitude, elevation_m, description) VALUES (?, ?, ?, ?, ?)",
            (name, lat, lon, elev, desc),
        )
        self.conn.commit()
        return cursor.lastrowid

    # ── Catalog Sync Log ────────────────────────────────────────

    def log_sync(
        self,
        added: int,
        updated: int,
        total: int,
        source: str = "space-track",
        status: str = "success",
        error: str | None = None,
    ):
        """Log a catalog sync operation."""
        self.conn.execute(
            """INSERT INTO catalog_sync_log
               (satellites_added, satellites_updated, total_in_catalog, source, status, error_message)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (added, updated, total, source, status, error),
        )
        self.conn.commit()

    def get_sync_history(self, limit: int = 20) -> list[dict]:
        """Get recent sync history."""
        rows = self.conn.execute(
            "SELECT * FROM catalog_sync_log ORDER BY sync_time DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
