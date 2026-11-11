import os
from datetime import datetime, timedelta
from itertools import combinations

import numpy as np
import pandas as pd
import requests
from skyfield.api import EarthSatellite, load, utc


def fetch_all_active_tles(username, password):
    session = requests.Session()
    login_url = "https://www.space-track.org/ajaxauth/login"
    tle_url = (
        "https://www.space-track.org/basicspacedata/query/class/tle_latest/"
        "ORDINAL/1/EPOCH/>now-30/DECAYED/false/format/json"
    )

    login = session.post(login_url, data={"identity": username, "password": password})
    if login.status_code != 200:
        raise Exception("Login to space-track failed")

    response = session.get(tle_url)
    if response.status_code != 200:
        raise Exception("Failed to fetch TLE data")

    tle_json = response.json()
    tle_data = []
    for entry in tle_json:
        name = entry.get("OBJECT_NAME", "Unknown")
        tle1 = entry.get("TLE_LINE1")
        tle2 = entry.get("TLE_LINE2")
        if tle1 and tle2:
            tle_data.append((name, tle1, tle2))

    return tle_data


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
                warnings.append(
                    {
                        "time_utc": t.utc_strftime("%Y-%m-%d %H:%M:%S"),
                        "satellite_1": name1,
                        "satellite_2": name2,
                        "distance_km": distance,
                    }
                )
    return warnings


def main():
    ts = load.timescale()
    now = datetime.now(utc)
    times = [ts.utc(now + timedelta(minutes=i)) for i in range(0, 60, 10)]

    username = os.environ.get("SPACETRACK_USERNAME")
    password = os.environ.get("SPACETRACK_PASSWORD")
    if not username or not password:
        raise SystemExit("Set SPACETRACK_USERNAME and SPACETRACK_PASSWORD (free account at space-track.org).")
    print("Fetching active satellite TLEs from space-track.org...")
    tle_data = fetch_all_active_tles(username, password)
    print(f"✅ Fetched {len(tle_data)} satellites")

    satellites = load_satellites(tle_data)
    print("Running conjunction analysis...")
    warnings = check_conjunctions(satellites, times)

    df = pd.DataFrame(warnings)
    df.to_csv("conjunction-warning.csv", index=False)
    print("✅ Conjunction analysis complete. Output saved to conjunction-warning.csv")


if __name__ == "__main__":
    main()
