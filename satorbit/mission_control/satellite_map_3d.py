from datetime import datetime, timezone

import plotly.graph_objects as go
from skyfield.api import load, wgs84

from .utils import get_active_satellites, get_ground_station


def generate_3d_map(output_path="static/satellite_track_3d.html"):
    try:
        satellites, _ = get_active_satellites()
        station_pos, station_info = get_ground_station()

        if not satellites:
            return False

        ts = load.timescale()
        now = datetime.now(timezone.utc)
        fig = go.Figure()

        # Neon Colors
        colors = ["#00f2ff", "#ff00ea", "#00ff88", "#ffea00", "#ff4d4d"]

        for i, satellite in enumerate(satellites):
            lats, lons = [], []
            for minutes in range(0, 180, 5):
                t = ts.utc(now.year, now.month, now.day, now.hour, now.minute + minutes)
                geocentric = satellite.at(t)
                subpoint = wgs84.subpoint(geocentric)
                lats.append(subpoint.latitude.degrees)
                lons.append(subpoint.longitude.degrees)

            color = colors[i % len(colors)]
            # Orbit Line
            fig.add_trace(
                go.Scattergeo(
                    lat=lats,
                    lon=lons,
                    mode="lines",
                    line=dict(width=2, color=color),
                    name=satellite.name,
                    hoverinfo="text",
                    text=f"Satellite: {satellite.name}",
                )
            )
            # LIVE Marker
            fig.add_trace(
                go.Scattergeo(
                    lat=[lats[0]],
                    lon=[lons[0]],
                    mode="markers",
                    marker=dict(size=10, color=color, symbol="circle", line=dict(width=2, color="white")),
                    name=f"{satellite.name} (LIVE)",
                )
            )

        # Ground Station - Minimalist
        fig.add_trace(
            go.Scattergeo(
                lat=[station_info["latitude"]],
                lon=[station_info["longitude"]],
                mode="markers+text",
                marker=dict(size=12, color="#ffffff", symbol="star"),
                text=[station_info["name"]],
                textposition="top center",
                name="Base Station",
            )
        )

        fig.update_geos(
            projection_type="orthographic",
            showland=True,
            landcolor="#1a1c22",
            showocean=True,
            oceancolor="#0b0e14",
            showcountries=True,
            countrycolor="#30363d",
            showcoastlines=True,
            coastlinecolor="#30363d",
            bgcolor="rgba(0,0,0,0)",  # Şeffaf arka plan
            framecolor="#30363d",
        )

        fig.update_layout(
            showlegend=True,
            legend=dict(x=0.02, y=0.98, bgcolor="rgba(0,0,0,0.5)", font=dict(color="white", size=10)),
            margin=dict(l=0, r=0, t=0, b=0),  # Kenar boşluklarını sıfırla
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            hovermode="closest",
        )

        fig.write_html(output_path, include_plotlyjs="cdn", full_html=True)
        print(f"✅ 3D Harita (Premium) güncellendi: {output_path}")
        return True
    except Exception as e:
        print(f"❌ 3D Harita hatası: {e}")
        return False


if __name__ == "__main__":
    generate_3d_map("satellite_track_3d.html")
