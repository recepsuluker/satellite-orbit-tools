"""Pass Predictions / Visibility page."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # source checkout


import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from satorbit.database.manager import SatelliteDB
from satorbit.database.models import initialize_database
from satorbit.engine.orbit_propagator import propagate_satellite
from satorbit.engine.visibility_calculator import GroundStation, calculate_passes
from satorbit.utils.export import passes_to_csv

initialize_database()

st.set_page_config(page_title="Pass Predictions — Satellite Orbit Tools", layout="wide", page_icon="📡")
st.markdown("## 📡 Pass Predictions")
st.caption("Calculate when satellites will be visible from your ground station.")

# ── Ground Station ───────────────────────────────────────────────
st.markdown("### Ground Station")
col_station, col_custom = st.columns(2)

with col_station:
    with SatelliteDB() as db:
        stations = db.get_ground_stations()

    station_options = {s["name"]: s for s in stations} if stations else {}
    use_custom = st.checkbox("Use custom location")

    if not use_custom and station_options:
        selected_name = st.selectbox("Select Station", list(station_options.keys()))
        station_data = station_options[selected_name]
        station = GroundStation(
            name=station_data["name"],
            latitude=station_data["latitude"],
            longitude=station_data["longitude"],
            elevation_m=station_data["elevation_m"],
        )
    else:
        use_custom = True

with col_custom:
    if use_custom:
        custom_name = st.text_input("Station Name", "My Station")
        custom_lat = st.number_input(
            "Latitude", value=28.5721, min_value=-90.0, max_value=90.0, format="%.4f"
        )
        custom_lon = st.number_input(
            "Longitude", value=-80.6480, min_value=-180.0, max_value=180.0, format="%.4f"
        )
        custom_elev = st.number_input("Elevation (m)", value=0.0, min_value=0.0)
        station = GroundStation(custom_name, custom_lat, custom_lon, custom_elev)

# ── Satellite Selection ──────────────────────────────────────────
st.markdown("### Satellite")
sat_input = st.number_input("NORAD ID", value=25544, min_value=1, step=1)

# ── Parameters ───────────────────────────────────────────────────
col_p1, col_p2 = st.columns(2)
with col_p1:
    pred_hours = st.slider("Prediction Window (hours)", 6, 168, 48)
with col_p2:
    min_elev = st.slider("Minimum Elevation (°)", 0, 45, 10)

# ── Calculate ────────────────────────────────────────────────────
if st.button("Calculate Passes", type="primary"):
    with SatelliteDB() as db:
        sat = db.get_satellite(int(sat_input))

    if not sat:
        st.error(f"Satellite NORAD {sat_input} not found in catalog.")
    else:
        with st.spinner(f"Calculating passes for {sat['name']}..."):
            prop = propagate_satellite(
                sat["tle_line1"],
                sat["tle_line2"],
                duration_hours=pred_hours,
                step_minutes=0.5,
                name=sat["name"],
            )

            if prop.error:
                st.error(f"Propagation error: {prop.error}")
            else:
                result = calculate_passes(prop, station, min_elev)

                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Passes", len(result.passes))
                c2.metric("Prediction Window", f"{result.analysis_window_hours:.0f}h")
                c3.metric("Station", station.name)

                if result.passes:
                    # Pass table
                    st.markdown("### Pass Schedule")
                    df = pd.DataFrame(
                        [
                            {
                                "AOS": p.aos_time.strftime("%Y-%m-%d %H:%M:%S"),
                                "AOS Az": f"{p.aos_azimuth:.0f}°",
                                "MAX": p.max_time.strftime("%H:%M:%S"),
                                "Max El": f"{p.max_elevation:.1f}°",
                                "LOS": p.los_time.strftime("%H:%M:%S"),
                                "LOS Az": f"{p.los_azimuth:.0f}°",
                                "Duration": f"{p.duration_seconds:.0f}s",
                                "Distance (km)": f"{p.max_distance_km:.0f}",
                            }
                            for p in result.passes
                        ]
                    )
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    # Elevation polar chart for best pass
                    best_pass = max(result.passes, key=lambda p: p.max_elevation)
                    st.markdown(f"### Best Pass — Max Elevation {best_pass.max_elevation:.1f}°")

                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatterpolar(
                            r=[90 - best_pass.max_elevation],
                            theta=[best_pass.max_azimuth],
                            mode="markers+text",
                            marker=dict(size=15, color="#60a5fa"),
                            text=[f"{best_pass.max_elevation:.1f}°"],
                            textposition="top center",
                            name="Peak",
                        )
                    )
                    fig.add_trace(
                        go.Scatterpolar(
                            r=[90 - 0],
                            theta=[best_pass.aos_azimuth],
                            mode="markers",
                            marker=dict(size=10, color="#22c55e", symbol="triangle-up"),
                            name="AOS (Rise)",
                        )
                    )
                    fig.add_trace(
                        go.Scatterpolar(
                            r=[90 - 0],
                            theta=[best_pass.los_azimuth],
                            mode="markers",
                            marker=dict(size=10, color="#ef4444", symbol="triangle-down"),
                            name="LOS (Set)",
                        )
                    )
                    fig.update_layout(
                        polar=dict(
                            radialaxis=dict(range=[0, 90], dtick=30, gridcolor="#1e293b"),
                            angularaxis=dict(
                                direction="clockwise",
                                gridcolor="#1e293b",
                                ticktext=["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
                                tickvals=[0, 45, 90, 135, 180, 225, 270, 315],
                            ),
                            bgcolor="rgba(0,0,0,0)",
                        ),
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="#e0e0e0",
                        showlegend=True,
                        height=400,
                        margin=dict(t=30, b=30),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Export
                    csv_data = passes_to_csv(result)
                    st.download_button(
                        "Download Pass Schedule (CSV)", csv_data, "pass_predictions.csv", "text/csv"
                    )
                else:
                    st.warning(f"No passes found above {min_elev}° elevation in the next {pred_hours} hours.")
