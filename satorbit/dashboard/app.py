"""Satellite Orbit Tools — Streamlit Main Application."""

import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # source checkout

import streamlit as st

from satorbit.database.models import initialize_database
from satorbit.logging_config import setup_logging

# Initialize on first run
setup_logging()
initialize_database()

# ── Page Config ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Satellite Orbit Tools",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for OpenClaw-inspired dark theme ─────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Global */
.stApp {
    font-family: 'Inter', sans-serif;
}

/* Hide default Streamlit elements */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1628 0%, #0a0e1a 100%);
    border-right: 1px solid #1e293b;
}

[data-testid="stSidebar"] .stMarkdown h1 {
    color: #60a5fa;
    font-size: 1.3rem;
    font-weight: 700;
    letter-spacing: -0.02em;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #1a1f35 0%, #151929 100%);
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 1rem;
}

[data-testid="stMetricValue"] {
    color: #60a5fa;
    font-weight: 700;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    padding: 0.5rem 1.5rem;
    transition: all 0.2s;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: #1a1f35;
    border-radius: 10px;
    padding: 4px;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    color: #888;
    font-weight: 500;
}

.stTabs [aria-selected="true"] {
    background: #252b45;
    color: #60a5fa;
}

/* DataFrames */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
}

/* Expander */
.streamlit-expanderHeader {
    background: #1a1f35;
    border-radius: 8px;
}

/* Status badges */
.risk-high { color: #ef4444; font-weight: 700; }
.risk-medium { color: #f59e0b; font-weight: 700; }
.risk-low { color: #22c55e; font-weight: 700; }

/* Hero section */
.hero-title {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.25rem;
}

.hero-subtitle {
    color: #64748b;
    font-size: 1rem;
    margin-bottom: 2rem;
}

/* Cards */
.info-card {
    background: linear-gradient(135deg, #1a1f35 0%, #151929 100%);
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}

.info-card h3 {
    color: #60a5fa;
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
}

.info-card .value {
    font-size: 1.8rem;
    font-weight: 700;
    color: #e0e0e0;
}

/* Animation for live indicator */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.live-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    background: #22c55e;
    border-radius: 50%;
    margin-right: 6px;
    animation: pulse 2s infinite;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Sidebar ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# Satellite Orbit Tools")
    st.markdown("*Real-time Collision Detection*")
    st.markdown("---")

    st.markdown('<span class="live-dot"></span> **System Active**', unsafe_allow_html=True)

    from satorbit.database.manager import SatelliteDB

    with SatelliteDB() as db:
        sat_count = db.get_satellite_count()
        stations = db.get_ground_stations()
        recent_events = db.get_recent_conjunctions(5)

    st.metric("Satellites in Catalog", f"{sat_count:,}")
    st.metric("Ground Stations", len(stations))
    st.metric("Recent Conjunctions", len(recent_events))

    st.markdown("---")
    st.markdown("**Quick Links**")
    st.page_link("pages/01_dashboard.py", label="Dashboard", icon="📊")
    st.page_link("pages/02_collision_analysis.py", label="Collision Analysis", icon="⚠️")
    st.page_link("pages/03_visibility.py", label="Pass Predictions", icon="📡")
    st.page_link("pages/04_3d_view.py", label="3D Visualization", icon="🌍")
    st.page_link("pages/05_reports.py", label="Reports & Export", icon="📄")

    st.markdown("---")
    st.caption("v1.0.0 | Powered by SGP4 + Rust")

# ── Main Content ────────────────────────────────────────────────
st.markdown('<div class="hero-title">Satellite Orbit Tools</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">'
    "Real-time satellite collision detection and monitoring system — "
    "powered by SGP4 propagation, Rust engine, and Redis caching"
    "</div>",
    unsafe_allow_html=True,
)

# Summary cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Satellites", f"{sat_count:,}", help="Active satellites in database")
with col2:
    high_risk = sum(1 for e in recent_events if (e.get("risk_score") or 0) >= 70)
    st.metric("High Risk Events", high_risk, delta=None)
with col3:
    st.metric("Ground Stations", len(stations))
with col4:
    from satorbit.engine.cache import get_cache_stats

    cache = get_cache_stats()
    st.metric("Cache Status", "Active" if cache.get("available") else "Offline")

st.markdown("---")

# Feature overview
col_a, col_b = st.columns(2)

with col_a:
    st.markdown("### Features")
    st.markdown("""
    - **Live TLE Data** — Fetch real-time satellite data from Space-Track.org
    - **Collision Analysis** — Detect close approaches with risk scoring
    - **Pass Predictions** — Calculate satellite visibility from ground stations
    - **2D/3D Visualization** — Interactive maps and 3D globe views
    - **CSV/HTML Reports** — Export analysis results
    - **WebSocket Dashboard** — Real-time position updates
    - **Redis Caching** — 450x faster repeated analyses
    - **Rust Engine** — 9x faster orbit computations
    """)

with col_b:
    st.markdown("### System Architecture")
    st.code(
        """
    ┌─────────────────────────────────────┐
    │          Streamlit Frontend          │
    ├──────────┬──────────┬───────────────┤
    │ Dashboard│ Analysis │ 3D View       │
    ├──────────┴──────────┴───────────────┤
    │      FastAPI + WebSocket Backend    │
    ├─────────┬───────────┬───────────────┤
    │  SGP4   │ Rust Eng. │ Redis Cache   │
    ├─────────┴───────────┴───────────────┤
    │   SQLite (66k+ satellite catalog)   │
    ├─────────────────────────────────────┤
    │      Space-Track.org API Feed       │
    └─────────────────────────────────────┘
    """,
        language="text",
    )

# Recent conjunction events
if recent_events:
    st.markdown("### Recent Conjunction Events")
    import pandas as pd

    df = pd.DataFrame(recent_events)
    display_cols = ["detected_at", "sat_a_name", "sat_b_name", "distance_km", "risk_score"]
    available = [c for c in display_cols if c in df.columns]
    if available:
        st.dataframe(
            df[available].rename(
                columns={
                    "detected_at": "Detected",
                    "sat_a_name": "Satellite A",
                    "sat_b_name": "Satellite B",
                    "distance_km": "Distance (km)",
                    "risk_score": "Risk Score",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info("No conjunction events recorded yet. Run a collision analysis to generate data.")
