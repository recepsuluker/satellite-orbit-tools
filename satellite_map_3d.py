from skyfield.api import load, EarthSatellite, wgs84, utc
from datetime import datetime, timedelta
import plotly.graph_objects as go

def main():
    # TLE data
    tle_line1 = "1 52739U 22057H   22159.11954099  .00002612  00000+0  15663-3 0  9993"
    tle_line2 = "2 52739  97.5193 273.9452 0009301 198.3423 161.7473 15.11805174  2023"
    satellite = EarthSatellite(tle_line1, tle_line2, "OBJECT H")

    ts = load.timescale()
    now = datetime.now(utc)

    # Collect positions ( like every 5 minutes for 3 hours)
    lats, lons = [], []
    for minutes in range(0, 180, 5):
        t = ts.utc(now.year, now.month, now.day, now.hour, now.minute + minutes)
        geocentric = satellite.at(t)
        subpoint = wgs84.subpoint(geocentric)
        lats.append(subpoint.latitude.degrees)
        lons.append(subpoint.longitude.degrees)

    # 3D Earth map
    fig = go.Figure()

    # Satellite track (red line)
    fig.add_trace(go.Scattergeo(
        lat=lats,
        lon=lons,
        mode='lines+markers',
        line=dict(width=2, color='red'),
        marker=dict(size=4, color='blue'),
        name='Uydu Yolu'
    ))

    # Earth map settings
    fig.update_geos(
        projection_type="orthographic",
        showland=True, landcolor="rgb(243, 243, 243)",
        showocean=True, oceancolor="LightBlue",
        showcountries=True,
    )

    fig.update_layout(
        title="3D Dünya Üzerinde Uydu Takibi",
        margin=dict(l=0, r=0, t=30, b=0)
    )

    fig.write_html("satellite_track_3d.html")
    print("✅ created 3D map: satellite_track_3d.html")

if __name__ == "__main__":
    main()
