# 🛰️ Satellite Collision Detection & Visualization Platform

This project is a modular toolkit for simulating, analyzing, and visualizing satellite orbits, pass predictions, and potential conjunction events.

---

## 📁 Project Structure

```
📦 SatelliteProject
├── orbit_tracker.py                 # Predict satellite positions from TLE
├── ground_pass_checker.py          # Predict pass events for a given ground station
├── satellite_map_2d.py             # 2D map visualization using folium
├── satellite_map_3d.py             # 3D globe visualization using Plotly
├── multi_conjunction_checker.py    # Multi-satellite collision detection
├── ConjunctionDashboard.jsx        # React-based web dashboard
├── requirements.txt                # Python dependencies
└── conjunction_warnings.csv        # (Optional) Output file for conjunction alerts
```

---

## 🚀 Features

- 🛰️ Orbit propagation using real-time TLE data
- 📡 Ground station pass prediction (AOS, MAX, LOS with azimuth/elevation)
- 🌍 2D and 3D satellite tracking on global maps
- 🚨 Conjunction (collision) detection between multiple satellites
- 🌐 Web dashboard with:
  - One-click analysis
  - Downloadable CSV output
  - Real-time user feedback

---

## 📦 Installation

```bash
# Clone the repo
git clone https://github.com/your-username/satellite-project.git
cd satellite-project

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

---

## 🧪 Run Modules

```bash
# Predict current satellite location (CSV output)
python orbit_tracker.py

# Pass prediction for a ground station
python ground_pass_checker.py

# Generate 2D map
python satellite_map_2d.py

# Generate 3D globe visualization
python satellite_map_3d.py

# Check for collisions between satellites
python multi_conjunction_checker.py
```

---

## 🌐 Run Web Dashboard (will be publishing as soon!!!)

```bash
# Navigate to React project (if using Vite/Next.js etc.)
cd web-dashboard

# Install and start dev server
npm install
npm run dev
```

---

## 📝 Notes

- TLE data should be updated regularly from [Celestrak](https://celestrak.com) or [Space-Track](https://www.space-track.org)
- Collision analysis is based on simplified distance threshold (e.g., <10 km)
- This project is ideal for hackathons, education, and early-stage mission analysis

---

by Recep Suluker

MIT License
=======
# satellite-orbit-tools
>>>>>>> 8685754533fd8ba3f59801efd51c9ef5d723647d
