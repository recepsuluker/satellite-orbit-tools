"""Dashboard page — satellite catalog overview and real-time tracking."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # source checkout


import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from satorbit.database.manager import SatelliteDB
from satorbit.database.models import initialize_database
from satorbit.engine.orbit_propagator import propagate_satellite

initialize_database()

st.set_page_config(page_title="Dashboard — Satellite Orbit Tools", layout="wide", page_icon="📊")
st.markdown("## 📊 Dashboard")

# ── Catalog Stats ────────────────────────────────────────────────
with SatelliteDB() as db:
    total = db.get_satellite_count()
    type_stats = db.get_object_type_stats()
    stations = db.get_ground_stations()
    recent = db.get_recent_conjunctions(20)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Satellites", f"{total:,}")
col2.metric("Object Types", len(type_stats))
col3.metric("Ground Stations", len(stations))
col4.metric("Recent Events", len(recent))

# ── Catalog Distribution ────────────────────────────────────────
if type_stats:
    st.markdown("### Satellite Catalog Distribution")
    df_types = pd.DataFrame(type_stats)
    fig = px.pie(
        df_types,
        values="count",
        names="object_type",
        color_discrete_sequence=px.colors.sequential.Blues_r,
        hole=0.4,
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0",
        margin=dict(t=30, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Satellite Search ────────────────────────────────────────────
st.markdown("### Satellite Search")
col_search, col_filter = st.columns([3, 1])

with col_search:
    search_query = st.text_input("Search by name or NORAD ID", placeholder="ISS, STARLINK, 25544...")
with col_filter:
    type_options = ["All"] + [t["object_type"] for t in type_stats] if type_stats else ["All"]
    selected_type = st.selectbox("Object Type", type_options)

if search_query or selected_type != "All":
    with SatelliteDB() as db:
        obj_type = selected_type if selected_type != "All" else None
        results = db.search_satellites(search_query, obj_type, limit=50)

    if results:
        df = pd.DataFrame(results)
        display = ["norad_id", "name", "object_type", "inclination", "period_min", "apogee_km", "perigee_km"]
        available = [c for c in display if c in df.columns]
        st.dataframe(
            df[available].rename(
                columns={
                    "norad_id": "NORAD ID",
                    "name": "Name",
                    "object_type": "Type",
                    "inclination": "Inc (°)",
                    "period_min": "Period (min)",
                    "apogee_km": "Apogee (km)",
                    "perigee_km": "Perigee (km)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("No satellites found matching your query.")

# ── Quick Track ─────────────────────────────────────────────────
st.markdown("### Quick Track")
st.caption("Enter a NORAD ID to visualize current satellite position on a 2D map.")

track_id = st.number_input("NORAD ID", value=25544, min_value=1, step=1)
track_hours = st.slider("Tracking window (hours)", 1, 24, 3)

if st.button("Track Satellite", type="primary"):
    with SatelliteDB() as db:
        sat = db.get_satellite(int(track_id))

    if not sat:
        st.error(f"Satellite {track_id} not in catalog. Import TLE data first.")
    else:
        with st.spinner(f"Propagating orbit for {sat['name']}..."):
            result = propagate_satellite(
                sat["tle_line1"],
                sat["tle_line2"],
                duration_hours=track_hours,
                step_minutes=1.0,
                name=sat["name"],
            )

        if result.error:
            st.error(f"Propagation error: {result.error}")
        elif result.positions:
            # Build dataframe
            df_pos = pd.DataFrame(
                [
                    {
                        "time": p.timestamp.strftime("%H:%M:%S"),
                        "lat": p.latitude,
                        "lon": p.longitude,
                        "alt_km": p.altitude_km,
                    }
                    for p in result.positions
                ]
            )

            # 2D map with Plotly
            fig = go.Figure()
            fig.add_trace(
                go.Scattergeo(
                    lat=df_pos["lat"],
                    lon=df_pos["lon"],
                    mode="lines+markers",
                    marker=dict(size=3, color="#60a5fa"),
                    line=dict(width=2, color="#3b82f6"),
                    name=sat["name"],
                    text=df_pos["time"],
                )
            )
            # Current position
            fig.add_trace(
                go.Scattergeo(
                    lat=[df_pos["lat"].iloc[0]],
                    lon=[df_pos["lon"].iloc[0]],
                    mode="markers",
                    marker=dict(size=12, color="#ef4444", symbol="star"),
                    name="Current Position",
                )
            )
            fig.update_geos(
                showland=True,
                landcolor="#1a1f35",
                showocean=True,
                oceancolor="#0a0e1a",
                showcoastlines=True,
                coastlinecolor="#334155",
                showframe=False,
                projection_type="equirectangular",
            )
            fig.update_layout(
                title=f"{sat['name']} — {track_hours}h Track",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e0e0e0",
                geo=dict(bgcolor="rgba(0,0,0,0)"),
                margin=dict(t=50, b=20, l=20, r=20),
                height=500,
            )
            st.plotly_chart(fig, use_container_width=True)

            # Stats
            c1, c2, c3 = st.columns(3)
            c1.metric("Min Altitude", f"{df_pos['alt_km'].min():.1f} km")
            c2.metric("Max Altitude", f"{df_pos['alt_km'].max():.1f} km")
            c3.metric("Positions Computed", len(df_pos))

# ── Ground Stations ─────────────────────────────────────────────
if stations:
    st.markdown("### Ground Stations")
    df_stations = pd.DataFrame(stations)
    fig_st = go.Figure(
        go.Scattergeo(
            lat=df_stations["latitude"],
            lon=df_stations["longitude"],
            text=df_stations["name"],
            mode="markers+text",
            marker=dict(size=10, color="#22c55e", symbol="diamond"),
            textposition="top center",
            textfont=dict(color="#e0e0e0", size=10),
        )
    )
    fig_st.update_geos(
        showland=True,
        landcolor="#1a1f35",
        showocean=True,
        oceancolor="#0a0e1a",
        showcoastlines=True,
        coastlinecolor="#334155",
        showframe=False,
    )
    fig_st.update_layout(
        title="Ground Station Network",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0",
        geo=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=50, b=20),
        height=400,
    )
    st.plotly_chart(fig_st, use_container_width=True)
