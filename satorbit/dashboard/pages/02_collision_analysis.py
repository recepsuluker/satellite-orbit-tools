"""Collision Analysis page."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # source checkout


import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from satorbit.database.manager import SatelliteDB
from satorbit.database.models import initialize_database
from satorbit.engine.collision_detector import analyze_collisions
from satorbit.engine.orbit_propagator import propagate_satellite
from satorbit.utils.export import conjunction_events_to_csv, generate_html_report

initialize_database()

st.set_page_config(page_title="Collision Analysis — Satellite Orbit Tools", layout="wide", page_icon="⚠️")
st.markdown("## ⚠️ Collision Analysis")
st.caption("Detect close approaches between satellites and assess collision risk.")

# ── Configuration ────────────────────────────────────────────────
with st.expander("Analysis Configuration", expanded=True):
    col1, col2, col3 = st.columns(3)

    with col1:
        threshold = st.number_input(
            "Collision Threshold (km)", value=10.0, min_value=0.1, max_value=100.0, step=0.5
        )
    with col2:
        duration = st.slider("Analysis Window (hours)", 1, 72, 24)
    with col3:
        step = st.select_slider("Time Step (minutes)", [0.5, 1, 2, 5, 10], value=1)

# ── Satellite Selection ──────────────────────────────────────────
st.markdown("### Select Satellites")
mode = st.radio("Selection Mode", ["Search & Select", "NORAD ID List", "By Object Type"], horizontal=True)

selected_sats = []

if mode == "Search & Select":
    with SatelliteDB() as db:
        all_sats = db.search_satellites(limit=500)

    if all_sats:
        options = {f"{s['name']} (NORAD {s['norad_id']})": s for s in all_sats}
        chosen = st.multiselect(
            "Select satellites",
            list(options.keys()),
            help="Select 2 or more satellites for collision analysis",
        )
        selected_sats = [options[c] for c in chosen]
    else:
        st.warning("No satellites in catalog. Import TLE data first.")

elif mode == "NORAD ID List":
    ids_input = st.text_area(
        "Enter NORAD IDs (one per line or comma-separated)",
        placeholder="25544\n48274\n41765",
        height=100,
    )
    if ids_input:
        try:
            ids = [int(x.strip()) for x in ids_input.replace(",", "\n").split("\n") if x.strip()]
            with SatelliteDB() as db:
                for nid in ids:
                    sat = db.get_satellite(nid)
                    if sat:
                        selected_sats.append(sat)
                    else:
                        st.warning(f"NORAD {nid} not in catalog")
        except ValueError:
            st.error("Invalid NORAD ID format")

elif mode == "By Object Type":
    with SatelliteDB() as db:
        types = db.get_object_type_stats()
    if types:
        chosen_type = st.selectbox("Object Type", [t["object_type"] for t in types])
        max_count = st.slider("Max satellites", 2, 100, 20)
        with SatelliteDB() as db:
            selected_sats = db.search_satellites(object_type=chosen_type, limit=max_count)

st.info(f"**{len(selected_sats)} satellites selected** — minimum 2 required for analysis")

# ── Run Analysis ─────────────────────────────────────────────────
if st.button("Run Collision Analysis", type="primary", disabled=len(selected_sats) < 2):
    progress = st.progress(0, text="Propagating orbits...")

    # Propagate
    propagations = []
    for i, sat in enumerate(selected_sats):
        result = propagate_satellite(
            sat["tle_line1"],
            sat["tle_line2"],
            duration_hours=duration,
            step_minutes=step,
            name=sat["name"],
        )
        if not result.error:
            propagations.append(result)
        progress.progress((i + 1) / len(selected_sats), text=f"Propagating {sat['name']}...")

    progress.progress(0.8, text="Analyzing collisions...")

    # Analyze
    analysis = analyze_collisions(propagations, threshold)

    progress.progress(1.0, text="Analysis complete!")

    # ── Results ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Analysis Results")

    # Summary cards
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Pairs Checked", f"{analysis.total_pairs_checked:,}")
    c2.metric("Conjunctions", analysis.total_conjunctions)
    c3.metric("🔴 High Risk", analysis.high_risk_count)
    c4.metric("🟡 Medium Risk", analysis.medium_risk_count)
    c5.metric("🟢 Low Risk", analysis.low_risk_count)

    st.caption(f"Analysis completed in {analysis.analysis_duration_sec:.2f} seconds")

    if analysis.events:
        # Events table
        st.markdown("### Conjunction Events")
        df_events = pd.DataFrame(
            [
                {
                    "Time (UTC)": e.time.strftime("%Y-%m-%d %H:%M"),
                    "Satellite A": e.satellite_a,
                    "Satellite B": e.satellite_b,
                    "Distance (km)": round(e.distance_km, 3),
                    "Rel. Velocity (km/s)": round(e.relative_velocity_km_s, 2),
                    "Risk Score": e.risk_score,
                }
                for e in analysis.events
            ]
        )
        st.dataframe(df_events, use_container_width=True, hide_index=True)

        # Risk distribution chart
        st.markdown("### Risk Distribution")
        fig_risk = go.Figure(
            data=[
                go.Bar(
                    x=["High (70-100)", "Medium (30-70)", "Low (0-30)"],
                    y=[analysis.high_risk_count, analysis.medium_risk_count, analysis.low_risk_count],
                    marker_color=["#ef4444", "#f59e0b", "#22c55e"],
                )
            ]
        )
        fig_risk.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
            xaxis=dict(gridcolor="#1e293b"),
            yaxis=dict(gridcolor="#1e293b", title="Count"),
            margin=dict(t=30, b=30),
            height=300,
        )
        st.plotly_chart(fig_risk, use_container_width=True)

        # Distance over time
        st.markdown("### Distance Timeline")
        df_timeline = pd.DataFrame(
            [
                {
                    "Time": e.time,
                    "Distance (km)": e.distance_km,
                    "Pair": f"{e.satellite_a} — {e.satellite_b}",
                    "Risk": e.risk_score,
                }
                for e in analysis.events
            ]
        )
        fig_timeline = px.scatter(
            df_timeline,
            x="Time",
            y="Distance (km)",
            color="Risk",
            size="Risk",
            color_continuous_scale=["#22c55e", "#f59e0b", "#ef4444"],
            hover_data=["Pair"],
        )
        fig_timeline.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
            xaxis=dict(gridcolor="#1e293b"),
            yaxis=dict(gridcolor="#1e293b"),
            margin=dict(t=30, b=30),
            height=400,
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

        # Save to DB
        with SatelliteDB() as db:
            for event in analysis.events:
                db.save_conjunction_event(
                    {
                        "event_time": event.time.isoformat(),
                        "satellite_a_id": event.norad_id_a,
                        "satellite_b_id": event.norad_id_b,
                        "distance_km": event.distance_km,
                        "relative_vel": event.relative_velocity_km_s,
                        "risk_score": event.risk_score,
                        "lat_a": event.pos_a[0],
                        "lon_a": event.pos_a[1],
                        "alt_a": event.pos_a[2],
                        "lat_b": event.pos_b[0],
                        "lon_b": event.pos_b[1],
                        "alt_b": event.pos_b[2],
                    }
                )

        # Export buttons
        st.markdown("### Export Results")
        col_csv, col_html = st.columns(2)
        with col_csv:
            csv_data = conjunction_events_to_csv(analysis)
            st.download_button("Download CSV", csv_data, "collision_report.csv", "text/csv")
        with col_html:
            html_data = generate_html_report(analysis)
            st.download_button("Download HTML Report", html_data, "collision_report.html", "text/html")
    else:
        st.success("No conjunctions detected within the threshold distance. All clear!")

# ── History ──────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### Historical Conjunction Events")
with SatelliteDB() as db:
    history = db.get_recent_conjunctions(50)

if history:
    df_hist = pd.DataFrame(history)
    display_cols = ["detected_at", "sat_a_name", "sat_b_name", "distance_km", "risk_score", "event_time"]
    available = [c for c in display_cols if c in df_hist.columns]
    st.dataframe(
        df_hist[available].rename(
            columns={
                "detected_at": "Detected",
                "sat_a_name": "Satellite A",
                "sat_b_name": "Satellite B",
                "distance_km": "Distance (km)",
                "risk_score": "Risk Score",
                "event_time": "Event Time",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No historical events. Run an analysis to generate data.")
