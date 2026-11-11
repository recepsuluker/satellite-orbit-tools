"""Tests for the database layer."""


class TestDatabaseInitialization:
    def test_initialize_creates_tables(self, initialized_db):
        with initialized_db() as db:
            # Should be able to query satellites table
            count = db.get_satellite_count()
            assert count >= 0

    def test_default_ground_stations(self, initialized_db):
        with initialized_db() as db:
            stations = db.get_ground_stations()
            assert len(stations) >= 5
            names = [s["name"] for s in stations]
            assert "Kennedy Space Center" in names
            assert "Baikonur Cosmodrome" in names


class TestSatelliteCRUD:
    def test_upsert_and_get(self, initialized_db, sample_tle_iss):
        with initialized_db() as db:
            db.upsert_satellite(
                {
                    "norad_id": sample_tle_iss["norad_id"],
                    "name": sample_tle_iss["name"],
                    "tle_line1": sample_tle_iss["line1"],
                    "tle_line2": sample_tle_iss["line2"],
                }
            )
            db.conn.commit()

            sat = db.get_satellite(25544)
            assert sat is not None
            assert sat["name"] == "ISS (ZARYA)"
            assert sat["norad_id"] == 25544

    def test_search_by_name(self, initialized_db, sample_tle_iss):
        with initialized_db() as db:
            db.upsert_satellite(
                {
                    "norad_id": sample_tle_iss["norad_id"],
                    "name": sample_tle_iss["name"],
                    "tle_line1": sample_tle_iss["line1"],
                    "tle_line2": sample_tle_iss["line2"],
                }
            )
            db.conn.commit()

            results = db.search_satellites("ISS")
            assert len(results) >= 1
            assert any(s["norad_id"] == 25544 for s in results)

    def test_search_by_norad_id(self, initialized_db, sample_tle_iss):
        with initialized_db() as db:
            db.upsert_satellite(
                {
                    "norad_id": sample_tle_iss["norad_id"],
                    "name": sample_tle_iss["name"],
                    "tle_line1": sample_tle_iss["line1"],
                    "tle_line2": sample_tle_iss["line2"],
                }
            )
            db.conn.commit()

            results = db.search_satellites("25544")
            assert len(results) >= 1

    def test_upsert_batch(self, initialized_db, sample_tle_iss, sample_tle_starlink):
        with initialized_db() as db:
            batch = [
                {
                    "norad_id": sample_tle_iss["norad_id"],
                    "name": sample_tle_iss["name"],
                    "tle_line1": sample_tle_iss["line1"],
                    "tle_line2": sample_tle_iss["line2"],
                },
                {
                    "norad_id": sample_tle_starlink["norad_id"],
                    "name": sample_tle_starlink["name"],
                    "tle_line1": sample_tle_starlink["line1"],
                    "tle_line2": sample_tle_starlink["line2"],
                },
            ]
            added, updated = db.upsert_satellites_batch(batch)
            assert added + updated == 2

    def test_get_nonexistent(self, initialized_db):
        with initialized_db() as db:
            assert db.get_satellite(99999999) is None


class TestConjunctionEvents:
    def test_save_and_retrieve(self, initialized_db, sample_tle_iss, sample_tle_starlink):
        with initialized_db() as db:
            # First add satellites
            for tle in [sample_tle_iss, sample_tle_starlink]:
                db.upsert_satellite(
                    {
                        "norad_id": tle["norad_id"],
                        "name": tle["name"],
                        "tle_line1": tle["line1"],
                        "tle_line2": tle["line2"],
                    }
                )
            db.conn.commit()

            # Save event
            event_id = db.save_conjunction_event(
                {
                    "event_time": "2024-02-15T12:00:00",
                    "satellite_a_id": 25544,
                    "satellite_b_id": 44713,
                    "distance_km": 5.234,
                    "relative_vel": 12.5,
                    "risk_score": 85.0,
                    "lat_a": 28.5,
                    "lon_a": -80.6,
                    "alt_a": 408.0,
                    "lat_b": 28.6,
                    "lon_b": -80.5,
                    "alt_b": 550.0,
                }
            )
            assert event_id > 0

            events = db.get_recent_conjunctions(10)
            assert len(events) >= 1
            assert events[0]["distance_km"] == 5.234


class TestSyncLog:
    def test_log_sync(self, initialized_db):
        with initialized_db() as db:
            db.log_sync(100, 50, 1000, "test")
            history = db.get_sync_history()
            assert len(history) >= 1
            assert history[0]["satellites_added"] == 100
