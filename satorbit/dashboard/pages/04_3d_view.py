"""3D Visualization page — interactive 3D globe with satellite tracks."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # source checkout


import numpy as np
import plotly.graph_objects as go
import streamlit as st

from satorbit.database.manager import SatelliteDB
from satorbit.database.models import initialize_database
from satorbit.engine.orbit_propagator import propagate_satellite

initialize_database()

st.set_page_config(page_title="3D View — Satellite Orbit Tools", layout="wide", page_icon="🌍")
st.markdown("## 🌍 3D Satellite Visualization")
st.caption("Interactive 3D globe showing satellite orbits and ground stations.")

# ── Controls ─────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    sat_ids_input = st.text_input(
        "NORAD IDs (comma-separated)",
        value="25544",
        help="Enter one or more NORAD IDs",
    )
with col2:
    view_hours = st.slider("Orbit Duration (hours)", 1, 6, 2)
with col3:
    show_stations = st.checkbox("Show Ground Stations", value=True)

if st.button("Generate 3D View", type="primary"):
    try:
        norad_ids = [int(x.strip()) for x in sat_ids_input.split(",") if x.strip()]
    except ValueError:
        st.error("Invalid NORAD IDs")
        st.stop()

    # ── Build Globe ──────────────────────────────────────────────
    fig = go.Figure()

    # Earth sphere
    u = np.linspace(0, 2 * np.pi, 60)
    v = np.linspace(0, np.pi, 30)
    x_earth = 6371 * np.outer(np.cos(u), np.sin(v))
    y_earth = 6371 * np.outer(np.sin(u), np.sin(v))
    z_earth = 6371 * np.outer(np.ones(np.size(u)), np.cos(v))

    fig.add_trace(
        go.Surface(
            x=x_earth,
            y=y_earth,
            z=z_earth,
            colorscale=[[0, "#0a2463"], [0.5, "#1e6091"], [1, "#168aad"]],
            showscale=False,
            opacity=0.85,
            name="Earth",
            hoverinfo="skip",
        )
    )

    # Satellite orbits
    colors = ["#60a5fa", "#f59e0b", "#22c55e", "#ef4444", "#a78bfa", "#f97316"]

    with SatelliteDB() as db:
        for idx, nid in enumerate(norad_ids):
            sat = db.get_satellite(nid)
            if not sat:
                st.warning(f"NORAD {nid} not in catalog")
                continue

            result = propagate_satellite(
                sat["tle_line1"],
                sat["tle_line2"],
                duration_hours=view_hours,
                step_minutes=1.0,
                name=sat["name"],
            )

            if result.error or not result.positions:
                continue

            # Convert geodetic to ECEF for 3D plot
            xs, ys, zs = [], [], []
            for p in result.positions:
                r = 6371 + p.altitude_km
                lat_r = np.radians(p.latitude)
                lon_r = np.radians(p.longitude)
                xs.append(r * np.cos(lat_r) * np.cos(lon_r))
                ys.append(r * np.cos(lat_r) * np.sin(lon_r))
                zs.append(r * np.sin(lat_r))

            color = colors[idx % len(colors)]

            # Orbit path
            fig.add_trace(
                go.Scatter3d(
                    x=xs,
                    y=ys,
                    z=zs,
                    mode="lines",
                    line=dict(width=3, color=color),
                    name=sat["name"],
                    hovertext=[
                        f"{sat['name']}<br>{p.timestamp.strftime('%H:%M')}<br>Alt: {p.altitude_km:.0f} km"
                        for p in result.positions
                    ],
                    hoverinfo="text",
                )
            )

            # Current position marker
            fig.add_trace(
                go.Scatter3d(
                    x=[xs[0]],
                    y=[ys[0]],
                    z=[zs[0]],
                    mode="markers",
                    marker=dict(size=6, color=color, symbol="diamond"),
                    name=f"{sat['name']} (now)",
                    showlegend=False,
                )
            )

        # Ground stations
        if show_stations:
            stations = db.get_ground_stations()
            for s in stations:
                r = 6371 + (s["elevation_m"] / 1000)
                lat_r = np.radians(s["latitude"])
                lon_r = np.radians(s["longitude"])
                sx = r * np.cos(lat_r) * np.cos(lon_r)
                sy = r * np.cos(lat_r) * np.sin(lon_r)
                sz = r * np.sin(lat_r)
                fig.add_trace(
                    go.Scatter3d(
                        x=[sx],
                        y=[sy],
                        z=[sz],
                        mode="markers+text",
                        marker=dict(size=5, color="#22c55e", symbol="diamond"),
                        text=[s["name"]],
                        textposition="top center",
                        textfont=dict(size=9, color="#22c55e"),
                        name=s["name"],
                        showlegend=False,
                    )
                )

    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            bgcolor="#0a0e1a",
            aspectmode="data",
        ),
        paper_bgcolor="#0a0e1a",
        font_color="#e0e0e0",
        margin=dict(t=0, b=0, l=0, r=0),
        height=700,
        showlegend=True,
        legend=dict(
            bgcolor="rgba(26,31,53,0.8)",
            bordercolor="#1e293b",
            font=dict(color="#e0e0e0"),
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.success(f"Rendered {len(norad_ids)} satellite(s) on 3D globe")
