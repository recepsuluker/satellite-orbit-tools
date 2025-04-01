from skyfield.api import EarthSatellite, load, wgs84
from datetime import datetime
import pandas as pd





def main():
    # TLE data (exapmle 2 satellites)
    tle_line1 = "1 52739U 22057H   22159.11954099  .00002612  00000+0  15663-3 0  9993"
    tle_line2 = "2 52739  97.5193 273.9452 0009301 198.3423 161.7473 15.11805174  2023"

    # Create the satellite
    satellite = EarthSatellite(tle_line1, tle_line2, "OBJECT H")
    ts = load.timescale()

    # Today's date and hourly
    now = datetime.utcnow()
    times = ts.utc(now.year, now.month, now.day, range(0, 24))

    positions = []
    for t in times:
        geocentric = satellite.at(t)
        subpoint = wgs84.subpoint(geocentric)
        positions.append({
            "utc_time": t.utc_strftime('%Y-%m-%d %H:%M:%S'),
            "latitude_deg": subpoint.latitude.degrees,
            "longitude_deg": subpoint.longitude.degrees,
            "elevation_km": subpoint.elevation.km
        })

    df = pd.DataFrame(positions)
    df.to_csv("satellite_positions.csv", index=False)
    print("created 'satellite_positions.csv' file.")

if __name__ == "__main__":
    main()
