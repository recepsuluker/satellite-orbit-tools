from skyfield.api import load, EarthSatellite, wgs84, utc
from datetime import datetime, timedelta
import folium

def main():
    # TLE data
    tle_line1 = "1 52739U 22057H   22159.11954099  .00002612  00000+0  15663-3 0  9993"
    tle_line2 = "2 52739  97.5193 273.9452 0009301 198.3423 161.7473 15.11805174  2023"
    satellite = EarthSatellite(tle_line1, tle_line2, "OBJECT H")

    ts = load.timescale()
    now = datetime.now(utc)

    # get positions at specific intervals ( like every 10 minutes)
    points = []
    for minutes in range(0, 180, 10):  #  3 hours periods
        t = ts.utc(now.year, now.month, now.day, now.hour, now.minute + minutes)
        geocentric = satellite.at(t)
        subpoint = wgs84.subpoint(geocentric)
        points.append((subpoint.latitude.degrees, subpoint.longitude.degrees))

    #  Create a Folium map
    start_location = points[0]
    m = folium.Map(location=start_location, zoom_start=3)

    #   Add points and lines
    folium.Marker(location=start_location, tooltip="Start").add_to(m)
    folium.PolyLine(points, color="blue", weight=2.5, opacity=1).add_to(m)
    for lat, lon in points:
        folium.CircleMarker(location=(lat, lon), radius=3, color="red", fill=True).add_to(m)

    #  save HTML file
    m.save("satellite_track_2d.html")
    print("✅ created 2D map: satellite_track_2d.html")

if __name__ == "__main__":
    main()
