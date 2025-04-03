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
# Remove-Item -Recurse -Force .\venv


# Install Python dependencies
pip install -r requirements.txt

# library packages
pip install folium skyfield numpy pandas plotly

# if you need to upgrade of python 
python.exe -m pip install --upgrade pip


```
---

## 🧪 Run Modules

```bash
# Predict current satellite location (CSV output)
python orbit_tracker.py
# Print shown like this 

    : datetime.datetime.now(datetime.UTC).
    now = datetime.utcnow()
    created 'satellite_positions.csv' file.

# Pass prediction for a ground station
python ground_pass_checker.py
# Print shown like this 

    2025-04-02 06:49:44 UTC - AOS (Rise) - Azimuth: 194.1°, Elevation: 10.0°
    2025-04-02 06:53:11 UTC - MAX (Peak) - Azimuth: 261.3°, Elevation: 35.0°
    2025-04-02 06:56:40 UTC - LOS (Set) - Azimuth: 328.7°, Elevation: 10.0°
    2025-04-02 18:27:13 UTC - AOS (Rise) - Azimuth: 33.5°, Elevation: 10.0°
    2025-04-02 18:30:38 UTC - MAX (Peak) - Azimuth: 98.3°, Elevation: 32.0°
    2025-04-02 18:34:00 UTC - LOS (Set) - Azimuth: 163.0°, Elevation: 10.0°
    2025-04-02 20:03:13 UTC - AOS (Rise) - Azimuth: 306.0°, Elevation: 10.0°
    2025-04-02 20:04:14 UTC - MAX (Peak) - Azimuth: 290.2°, Elevation: 10.9°
    2025-04-02 20:05:15 UTC - LOS (Set) - Azimuth: 274.3°, Elevation: 10.0°




# Generate 2D map
python satellite_map_2d.py
# Print shown like this 

    ✅ created 2D map: satellite_track_2d.html


# Generate 3D globe visualization
python satellite_map_3d.py
# Print shown like this 

    ✅ created 3D map: satellite_track_3d.html


# Check for collisions between satellites
python multi_conjunction_checker.py
# Print shown like this 

    ✅ All clear. No close approaches detected.

```

'''
Just built a simple orbit visualization tool that maps satellite positions in real-time on:

* 2D world map using Leaflet (Folium)

 * 3D rotating globe using Plotly



Open the HTML file in your folder

Just double-click on the file or right-click → "Open with browser":
'''


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

=======
by Recep Suluker


