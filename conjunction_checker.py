from skyfield.api import load, EarthSatellite, wgs84, utc
from datetime import datetime, timedelta
import numpy as np

def main():
    # Example of two satellites (with orbits in the same time zone)
    tle1_line1 = "1 25544U 98067A   24121.54748843  .00010529  00000+0  19600-3 0  9998"
    tle1_line2 = "2 25544  51.6403  31.7951 0002961 118.7987  29.7956 15.50000778396301"

    tle2_line1 = "1 43013U 17073E   24121.51704920  .00002111  00000+0  15702-3 0  9993"
    tle2_line2 = "2 43013  97.2971 180.6960 0011321 156.3136 203.8684 15.05528181331280"

    satellite1 = EarthSatellite(tle1_line1, tle1_line2, "ISS (ZARYA)")
    satellite2 = EarthSatellite(tle2_line1, tle2_line2, "FLOCK 3P-1")

    ts = load.timescale()
    now = datetime.now(utc)

    # Time interval: Every 1 minute for 2 hours
    times = [ts.utc(now + timedelta(minutes=i)) for i in range(0, 120)]

    warnings = []

    for t in times:
        pos1 = satellite1.at(t).position.km
        pos2 = satellite2.at(t).position.km
        distance = np.linalg.norm(pos1 - pos2)

        if distance < 10:  # a warning if closer than 10 km
            warnings.append((t.utc_strftime('%Y-%m-%d %H:%M:%S'), distance))

    if warnings:
        print("🚨 Collision Warning: Close approaches detected!")
        for time_str, d in warnings:
            print(f"{time_str} UTC - Distance between satellites: {d:.2f} km")
    else:
        print("✅ All clear. No close approaches detected.")

if __name__ == "__main__":
    main()
