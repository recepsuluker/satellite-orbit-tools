from skyfield.api import load, EarthSatellite, wgs84, utc
from datetime import datetime, timedelta

def main():
    # TLE data (two satellite)
    tle_line1 = "1 52739U 22057H   22159.11954099  .00002612  00000+0  15663-3 0  9993"
    tle_line2 = "2 52739  97.5193 273.9452 0009301 198.3423 161.7473 15.11805174  2023"
    satellite = EarthSatellite(tle_line1, tle_line2, "OBJECT H")
    
    # Time scale
    ts = load.timescale()
    now = datetime.now(utc)
    start_time = ts.utc(now.year, now.month, now.day, now.hour)
    next_day = now + timedelta(days=1)
    end_time = ts.utc(next_day.year, next_day.month, next_day.day)

    # Ground station location [NASA Kennedy Space Center Ground Station (KSC)]
    station_lat = 28.572
    station_lon = -80.648
    station_elevation_m = 3  # Approximate altitude

    station = wgs84.latlon(latitude_degrees=station_lat,
                           longitude_degrees=station_lon,
                           elevation_m=station_elevation_m)

    # Find the visibility windows between the satellite and the ground station 
    t, events = satellite.find_events(station, start_time, end_time, altitude_degrees=10.0)

    # Interpret the events 
    event_names = ['AOS (Rise)', 'MAX (Peak)', 'LOS (Set)']
    for ti, event in zip(t, events):
        name = event_names[event]
        difference = satellite.at(ti) - station.at(ti)
        alt, az, distance = difference.altaz()
        print(f"{ti.utc_strftime('%Y-%m-%d %H:%M:%S')} UTC - {name} - Azimuth: {az.degrees:.1f}°, Elevation: {alt.degrees:.1f}°")

if __name__ == "__main__":
    main()
