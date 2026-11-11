from datetime import datetime, timezone

import folium
from folium.plugins import AntPath
from skyfield.api import load, wgs84

from .utils import get_active_satellites


def generate_2d_map(output_path="static/satellite_track_2d.html"):
    try:
        satellites, _ = get_active_satellites()
        if not satellites:
            return False

        ts = load.timescale()
        now = datetime.now(timezone.utc)

        m = folium.Map(location=[0, 0], zoom_start=2, tiles="CartoDB dark_matter", zoom_control=False)

        colors = ["#00f2ff", "#ff00ea", "#00ff88", "#ffea00", "#ff4d4d"]

        for i, satellite in enumerate(satellites):
            color = colors[i % len(colors)]
            segments = [[]]
            last_lon = None

            for minutes in range(0, 180, 5):
                t = ts.utc(now.year, now.month, now.day, now.hour, now.minute + minutes)
                geocentric = satellite.at(t)
                subpoint = wgs84.subpoint(geocentric)
                lat, lon = subpoint.latitude.degrees, subpoint.longitude.degrees

                if last_lon is not None and abs(lon - last_lon) > 180:
                    segments.append([])

                segments[-1].append((lat, lon))
                last_lon = lon

            # AntPath ile ANİMASYONLU YOL (Premium Look)
            for segment in segments:
                if len(segment) > 1:
                    AntPath(
                        locations=segment,
                        color=color,
                        weight=2,
                        opacity=0.8,
                        dash_array=[2, 10],
                        pulse_color="#ffffff",
                        delay=1000,
                        tooltip=satellite.name,
                    ).add_to(m)

            # Canlı merkez noktası
            if segments[0]:
                folium.CircleMarker(
                    location=segments[0][0],
                    radius=6,
                    color=color,
                    fill=True,
                    fill_opacity=1.0,
                    popup=f"LIVE: {satellite.name}",
                    weight=3,
                ).add_to(m)

        m.save(output_path)
        print(f"✅ Animasyonlu 2D Harita güncellendi: {output_path}")
        return True
    except Exception as e:
        print(f"❌ 2D Animasyon hatası: {e}")
        return False


if __name__ == "__main__":
    generate_2d_map("satellite_track_2d.html")
