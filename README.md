# 🛰️ Autonomous Multi-Agent Satellite Operations Platform

A professional, real-time satellite tracking and collision avoidance dashboard powered by an autonomous multi-agent architecture. Built for mission operators, constellation managers, and space situational awareness (SSA) professionals.

![Dashboard Preview](docs/dashboard_preview.png)

## 🚀 Key Features

### 🌍 Hybrid Visualization Engine
- **2D Mercator:** Smoothly animated satellite tracks using `AntPath` for orbital flow visualization.
- **3D Orthographic Globe:** Premium globe view showing full constellation geometry.
- **🔭 Sky-View Radar:** Topocentric polar plot (Azimuth/Elevation) for visual observers and ground station operations.

### 🤖 Multi-Agent Architecture
| Agent | Role | Frequency |
|-------|------|-----------|
| **Commander** | User interface & chat commands | On-demand |
| **Guardian** | Orbital collision hazard scanning | Every 30s (UI) |
| **Notify** | Gmail & Slack alerting | Every 30 min / Instant |
| **Auto-Sync** | TLE database synchronization + anomaly detection | Every 6 hours |
| **Mission Log** | System-wide activity monitoring | Real-time |

### 🔥 Maneuver Awareness Engine (v2.0)
1. **Maneuver Planning:** Schedule thrust burns for your satellites with Delta-V and duration parameters. The system adjusts risk calculations accordingly.
2. **TLE Drift & Jump Analysis:** Auto-Sync Agent compares incoming TLE data against previous snapshots. A Mean Motion jump > 0.005 triggers a **MANEUVER DETECTED** alert.
3. **Uncertainty Visualization:** Conjunction risks are tagged with uncertainty levels — `NORMAL`, `HIGH (Maneuver)`, or `PRECISION (CDM)` — so operators know how much to trust each data point.
4. **CDM Integration:** Upload Space-Track CDM (Conjunction Data Message) XML files for high-precision collision probability analysis.
5. **Open SSA Monitor:** Interface for monitoring amateur observer networks and external anomaly feeds.

### 📡 Omni-Channel Alerting
- **Gmail:** Automated status reports with CSV attachment every 30 minutes. Instant URGENT alerts on critical conjunction events.
- **Slack:** Rich webhook alerts with satellite names and risk counts.
- **Telegram:** Direct link integration for mobile access.
- **Space-Track:** Quick-access portal for professional SSA data.
- **Manual Refresh:** Hit "REFRESH SYSTEM" to trigger an instant status report to Gmail + Slack with current asset list.

### 📊 Additional Capabilities
- **Active Catalog Integration:** Search 8,000+ active satellites via Celestrak GP API.
- **Dynamic Pass Prediction:** AOS/MAX/LOS calculations for the next 24 hours.
- **City-Based Geocoding:** Search by city name (OpenStreetMap Nominatim) to set ground station location.
- **Conjunction Risk Analysis:** Real-time distance sorting with critical/warning thresholds and visual banners.

## 🛠️ Tech Stack

- **Backend:** Python 3.9+, FastAPI, Uvicorn
- **Orbital Mechanics:** SGP4 (TEME→ECEF), Skyfield, Celestrak API
- **Visualization:** Folium (Animated 2D), Plotly (3D & Polar Radar)
- **Alerting:** SMTP (Gmail), Slack Webhooks, Telegram Bot API
- **Data Formats:** TLE, CDM (XML), CSV
- **Frontend:** Modern Dark UI with Glassmorphism effects

## 🚀 Quick Start

1. **Clone & Setup:**
    ```bash
    git clone <repo-url>
    cd satellite-orbit-tools
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2. **Run the Control Center:**
    ```bash
    python3 app.py
    ```

3. **Access Dashboard:**
    Open [http://localhost:8000](http://localhost:8000) in your browser.

## ⚙️ Configuration

The system uses `config.json` for persistent storage. Manage everything via the UI:

| Setting | Location |
|---------|----------|
| **Ground Station** | Sidebar → OPS LOCATION (City search or manual Lat/Lon) |
| **Satellites** | Sidebar → ADD SATELLITE (Name or NORAD ID) |
| **Email Alerts** | `config.json` → email section (SMTP credentials) |
| **Slack Alerts** | `config.json` → slack section (Webhook URL) |
| **Maneuver Plans** | Sidebar → MANEUVER PLANNING |
| **CDM Data** | Sidebar → PRECISION ANALYSIS (Upload XML) |

## 📁 Project Structure

```
satellite-orbit-tools/
├── app.py                    # FastAPI main application + agent orchestration
├── notify_agent.py           # NotifyAgent: Email/Slack alerting engine
├── utils.py                  # TLE fetching, catalog management, geocoding
├── satellite_map_2d.py       # 2D Mercator map generator (Folium)
├── satellite_map_3d.py       # 3D Orthographic globe generator (Plotly)
├── satellite_sky_view.py     # Sky-View polar radar generator (Plotly)
├── config.json               # Runtime persisted settings (UI-managed)
├── conjunction-warning.csv   # Auto-generated collision risk data
├── templates/
│   └── index.html            # Mission Control Dashboard UI
├── static/                   # Generated map HTML files
├── SKILL.md                  # Project conventions & architecture docs
└── requirements.txt          # Python dependencies
```

## 🔄 Version History

| Version | Highlights |
|---------|-----------|
| **v2.0** | Maneuver Awareness Engine (5-step plan), CDM Integration, TLE Jump Detection, 30-min notification cycle, Open SSA Monitor |
| **v1.5** | Multi-Agent Architecture, Omni-channel Alerting (Gmail/Slack/Telegram), City Geocoding, Mission Terminal |
| **v1.0** | Core tracking, 2D/3D/Sky-View maps, Pass Prediction, Conjunction Analysis |

---
*Developed with ❤️ for space exploration and orbital safety.*
