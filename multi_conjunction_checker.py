from skyfield.api import load, EarthSatellite, utc
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from itertools import combinations

def load_satellites(tle_data):
    satellites = []
    for name, tle1, tle2 in tle_data:
        satellites.append(EarthSatellite(tle1, tle2, name))
    return satellites

def check_conjunctions(satellites, times, threshold_km=10):
    warnings = []
    for t in times:
        positions = {sat.name: sat.at(t).position.km for sat in satellites}
        for (name1, pos1), (name2, pos2) in combinations(positions.items(), 2):
            distance = np.linalg.norm(pos1 - pos2)
            if distance < threshold_km:
                warnings.append({
                    "time_utc": t.utc_strftime('%Y-%m-%d %H:%M:%S'),
                    "satellite_1": name1,
                    "satellite_2": name2,
                    "distance_km": distance
                })
    return warnings

def main():
    # TLE data (exapmle 5 satellites)
    tle_data = [
        ("ISS", 
         "1 25544U 98067A   24121.54748843  .00010529  00000+0  19600-3 0  9998",
         "2 25544  51.6403  31.7951 0002961 118.7987  29.7956 15.50000778396301"),
        ("FLOCK 3P-1", 
         "1 43013U 17073E   24121.51704920  .00002111  00000+0  15702-3 0  9993",
         "2 43013  97.2971 180.6960 0011321 156.3136 203.8684 15.05528181331280"),
        ("FLOCK 3P-2", 
         "1 43014U 17073F   24121.51383796  .00002141  00000+0  15873-3 0  9993",
         "2 43014  97.2971 180.7757 0011046 155.9485 204.2406 15.05528150331286"),
        ("FENGYUN 1C DEB", 
         "1 30698U 99025A   24121.55206940  .00001106  00000+0  59557-3 0  9994",
         "2 30698  99.1197 102.5944 0166644 141.3671 220.1045 14.07679601705703"),
        ("CZ-4C R/B", 
         "1 46014U 20063B   24121.53162290  .00000065  00000+0  29438-4 0  9996",
         "2 46014  97.5218 211.7251 0012741  80.4878 279.8012 14.83452480199300")
    ]

    satellites = load_satellites(tle_data)
    ts = load.timescale()
    now = datetime.now(utc)

    # 2-hour analysis interval (1-minute sampling)
    times = [ts.utc(now + timedelta(minutes=i)) for i in range(0, 120)]

    # Collision analysis
    warnings = check_conjunctions(satellites, times, threshold_km=10)

    if warnings:
        df = pd.DataFrame(warnings)
        df.to_csv("conjunction_warnings.csv", index=False)
        print("🚨 Close approach(es) detected and saved to CSV file: conjunction_warnings.csv")
    else:
        print("✅ No close approaches detected.")

if __name__ == "__main__":
    main()
