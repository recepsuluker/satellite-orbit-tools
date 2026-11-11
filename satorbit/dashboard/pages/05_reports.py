"""Reports & Export page."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # source checkout


import pandas as pd
import streamlit as st

from satorbit.database.manager import SatelliteDB
from satorbit.database.models import initialize_database
from satorbit.engine.cache import get_cache_stats

initialize_database()

st.set_page_config(page_title="Reports — Satellite Orbit Tools", layout="wide", page_icon="📄")
st.markdown("## 📄 Reports & System Status")

tab_events, tab_catalog, tab_system = st.tabs(["Conjunction Events", "Catalog Management", "System Status"])

# ── Tab 1: Conjunction Events ────────────────────────────────────
with tab_events:
    st.markdown("### Historical Conjunction Events")
    with SatelliteDB() as db:
        events = db.get_recent_conjunctions(200)

    if events:
        df = pd.DataFrame(events)
        display_cols = [
            "id",
            "detected_at",
            "event_time",
            "sat_a_name",
            "sat_b_name",
            "distance_km",
            "relative_vel",
            "risk_score",
        ]
        available = [c for c in display_cols if c in df.columns]

        # Filters
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            risk_filter = st.selectbox("Risk Level", ["All", "High (70+)", "Medium (30-70)", "Low (<30)"])
        with col_f2:
            sort_by = st.selectbox("Sort By", ["Risk Score (High→Low)", "Date (Recent)", "Distance (Close)"])

        filtered = df.copy()
        if risk_filter == "High (70+)":
            filtered = filtered[filtered["risk_score"] >= 70]
        elif risk_filter == "Medium (30-70)":
            filtered = filtered[(filtered["risk_score"] >= 30) & (filtered["risk_score"] < 70)]
        elif risk_filter == "Low (<30)":
            filtered = filtered[filtered["risk_score"] < 30]

        if sort_by == "Risk Score (High→Low)":
            filtered = filtered.sort_values("risk_score", ascending=False)
        elif sort_by == "Date (Recent)":
            filtered = filtered.sort_values("detected_at", ascending=False)
        elif sort_by == "Distance (Close)":
            filtered = filtered.sort_values("distance_km")

        st.dataframe(
            filtered[available].rename(
                columns={
                    "id": "ID",
                    "detected_at": "Detected",
                    "event_time": "Event Time",
                    "sat_a_name": "Satellite A",
                    "sat_b_name": "Satellite B",
                    "distance_km": "Distance (km)",
                    "relative_vel": "Rel. Vel (km/s)",
                    "risk_score": "Risk Score",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        # Export
        csv = filtered[available].to_csv(index=False)
        st.download_button("Export to CSV", csv, "conjunction_history.csv", "text/csv")
    else:
        st.info("No conjunction events recorded yet.")

# ── Tab 2: Catalog Management ────────────────────────────────────
with tab_catalog:
    st.markdown("### Satellite Catalog")
    with SatelliteDB() as db:
        total = db.get_satellite_count()
        type_stats = db.get_object_type_stats()
        sync_history = db.get_sync_history()

    st.metric("Total Satellites", f"{total:,}")

    if type_stats:
        st.markdown("#### Distribution by Object Type")
        df_types = pd.DataFrame(type_stats)
        st.dataframe(
            df_types.rename(columns={"object_type": "Type", "count": "Count"}),
            use_container_width=True,
            hide_index=True,
        )

    # Live sync from Space-Track / CelesTrak
    st.markdown("#### Fetch Live TLE Data")
    from satorbit.config import get_settings

    settings = get_settings()
    has_spacetrack = bool(settings.spacetrack_username and settings.spacetrack_password)

    col_src, col_grp, col_lim = st.columns([2, 2, 1])
    with col_src:
        source = st.selectbox(
            "Source",
            ["Space-Track.org", "CelesTrak", "Demo (offline)"]
            if has_spacetrack
            else ["CelesTrak", "Demo (offline)"],
        )
    with col_grp:
        if source == "Space-Track.org":
            st_group = st.selectbox("Object Type", ["PAYLOAD", "ROCKET BODY", "DEBRIS"])
        elif source == "CelesTrak":
            from satorbit.utils.celestrak_client import GROUPS

            st_group = st.selectbox("Group", list(GROUPS.keys()), index=0)
        else:
            st_group = "demo"
    with col_lim:
        if source == "Space-Track.org":
            fetch_limit = st.number_input("Limit", 100, 5000, 1000, step=100)
        else:
            fetch_limit = 0

    if st.button("Fetch & Sync", type="primary"):
        with st.spinner(f"Fetching from {source}..."):
            fetched = []
            sync_source = ""
            if source == "Demo (offline)":
                from satorbit.utils.celestrak_client import get_demo_satellites

                fetched = get_demo_satellites()
                sync_source = "demo"
            elif source == "CelesTrak":
                from satorbit.utils.celestrak_client import fetch_tle_group

                fetched = fetch_tle_group(st_group)
                sync_source = f"celestrak:{st_group}"
            elif source == "Space-Track.org":
                import asyncio

                from satorbit.utils.space_track_client import SpaceTrackClient

                async def _fetch():
                    async with SpaceTrackClient() as client:
                        return await client.fetch_tle_latest(object_type=st_group, limit=fetch_limit)

                fetched = asyncio.run(_fetch())
                sync_source = f"space-track:{st_group}"

            if fetched:
                with SatelliteDB() as db2:
                    added, updated = db2.upsert_satellites_batch(fetched)
                    new_total = db2.get_satellite_count()
                    db2.log_sync(added, updated, new_total, sync_source)
                st.success(
                    f"Synced {len(fetched)} satellites: {added} new, {updated} updated. Total: {new_total:,}"
                )
                st.rerun()
            else:
                st.error("No data fetched. Check credentials or network connection.")

    st.markdown("---")

    # Manual TLE import
    st.markdown("#### Import TLE Data")
    tle_text = st.text_area(
        "Paste TLE data (3-line format)",
        placeholder="ISS (ZARYA)\n1 25544U 98067A   ...\n2 25544  51.6416 ...",
        height=200,
    )

    if st.button("Import TLEs") and tle_text:
        from satorbit.utils.tle_parser import parse_tle_text

        parsed = parse_tle_text(tle_text)
        if parsed:
            sats = [
                {
                    "norad_id": t.norad_id,
                    "name": t.name,
                    "intl_designator": t.intl_designator,
                    "tle_line1": t.tle_line1,
                    "tle_line2": t.tle_line2,
                    "epoch": t.epoch.isoformat(),
                    "inclination": t.inclination,
                    "eccentricity": t.eccentricity,
                    "period_min": t.period_min,
                    "apogee_km": t.apogee_km,
                    "perigee_km": t.perigee_km,
                }
                for t in parsed
            ]
            with SatelliteDB() as db:
                added, updated = db.upsert_satellites_batch(sats)
                db.log_sync(added, updated, db.get_satellite_count(), "manual_import")
            st.success(f"Imported {added} new, updated {updated} existing satellites.")
            st.rerun()
        else:
            st.error("Could not parse any TLE data from the input.")

    # Sync History
    if sync_history:
        st.markdown("#### Sync History")
        st.dataframe(
            pd.DataFrame(sync_history),
            use_container_width=True,
            hide_index=True,
        )

# ── Tab 3: System Status ────────────────────────────────────────
with tab_system:
    st.markdown("### System Status")

    col_s1, col_s2 = st.columns(2)

    with col_s1:
        st.markdown("#### Cache (Redis)")
        cache = get_cache_stats()
        if cache.get("available"):
            st.success("Redis Connected")
            st.json(cache)
        else:
            st.warning("Redis Offline — caching disabled, operating in direct mode")

    with col_s2:
        st.markdown("#### Database")
        with SatelliteDB() as db:
            sat_count = db.get_satellite_count()
            station_count = len(db.get_ground_stations())
            event_count = len(db.get_recent_conjunctions(999))

        st.json(
            {
                "status": "connected",
                "satellites": sat_count,
                "ground_stations": station_count,
                "conjunction_events": event_count,
            }
        )

    st.markdown("#### API Endpoints")
    st.code(
        """
    GET  /                       → Health check
    GET  /docs                   → Swagger UI
    GET  /api/v1/satellites/     → List satellites
    GET  /api/v1/satellites/{id} → Get satellite
    GET  /api/v1/satellites/{id}/position → Propagate orbit
    POST /api/v1/collision/analyze → Run collision analysis
    GET  /api/v1/collision/history → Recent conjunctions
    POST /api/v1/collision/quick-check → Quick pair check
    GET  /api/v1/visibility/passes/{id} → Pass predictions
    GET  /api/v1/visibility/stations → List ground stations
    WS   /ws/track               → Real-time tracking
    WS   /ws/alerts              → Collision alerts
    """,
        language="text",
    )
