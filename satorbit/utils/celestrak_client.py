"""CelesTrak API client for fetching TLE data — no authentication required."""

from __future__ import annotations

import httpx

from satorbit.logging_config import get_logger
from satorbit.utils.tle_parser import parse_tle

logger = get_logger("utils.celestrak")

BASE_URL = "https://celestrak.org/NORAD/elements/gp.php"

# Popular satellite groups available on CelesTrak
GROUPS = {
    "stations": "Space Stations (ISS, Tiangong, etc.)",
    "active": "Active Satellites (~9000)",
    "starlink": "Starlink (~6000)",
    "oneweb": "OneWeb (~600)",
    "weather": "Weather Satellites",
    "science": "Science Satellites",
    "resource": "Earth Resources",
    "geo": "Geostationary Satellites",
    "gps-ops": "GPS Operational",
    "galileo": "Galileo",
    "amateur": "Amateur Radio",
    "visual": "Brightest (visible to naked eye, ~200)",
    "last-30-days": "Launched in Last 30 Days",
}

# Bundled demo TLEs for offline/testing use
DEMO_TLES = """\
ISS (ZARYA)
1 25544U 98067A   24045.51792824  .00016717  00000-0  29820-3 0  9992
2 25544  51.6412 236.2420 0004448  38.8780  36.1584 15.49953808440497
TIANGONG
1 48274U 21035A   24045.50000000  .00018300  00000-0  21150-3 0  9991
2 48274  41.4700 131.1600 0006340 286.8400  73.1400 15.62250000140001
STARLINK-1007
1 44713U 19074A   24045.54326621  .00001584  00000-0  11834-3 0  9999
2 44713  53.0541 242.9636 0001406  85.4385 274.6779 15.06388506244765
STARLINK-1008
1 44714U 19074B   24045.53421789  .00001723  00000-0  12456-3 0  9998
2 44714  53.0539 242.9512 0001398  86.1234 273.9876 15.06401234244789
STARLINK-1009
1 44715U 19074C   24045.52516957  .00001654  00000-0  12145-3 0  9997
2 44715  53.0537 242.9388 0001410  84.7654 275.3456 15.06374567244812
HUBBLE
1 20580U 90037B   24045.48000000  .00000980  00000-0  49700-4 0  9995
2 20580  28.4700 117.3500 0002610 112.0300 248.0500 15.09412345678901
NOAA 15
1 25338U 98030A   24045.50000000  .00000057  00000-0  52800-4 0  9998
2 25338  98.7240  58.1850 0010400 142.3200 217.8700 14.25952800340001
NOAA 18
1 28654U 05018A   24045.50000000  .00000042  00000-0  38700-4 0  9997
2 28654  99.0430 118.5900 0014200  51.6700 308.5600 14.12345678901234
NOAA 19
1 33591U 09005A   24045.50000000  .00000048  00000-0  42300-4 0  9996
2 33591  99.1620 330.4100 0014050 106.8900 253.3700 14.12567890123456
TERRA
1 25994U 99068A   24045.50000000  .00000120  00000-0  32700-4 0  9993
2 25994  98.2100  82.3100 0001200 100.5400 259.5800 14.57123456789012
AQUA
1 27424U 02022A   24045.50000000  .00000140  00000-0  37200-4 0  9992
2 27424  98.2080 199.5300 0001800  87.1200 272.9900 14.57234567890123
LANDSAT 8
1 39084U 13008A   24045.50000000  .00000063  00000-0  19700-4 0  9991
2 39084  98.2200  89.4500 0001400 103.1200 257.0100 14.57112345678901
GPS BIIR-2
1 24876U 97035A   24045.50000000  .00000011  00000-0  10000-3 0  9990
2 24876  55.4800  42.5600 0056900 245.1200 114.4500 2.00565800195001
GPS BIIR-3
1 25030U 97067A   24045.50000000  .00000009  00000-0  10000-3 0  9989
2 25030  54.3400 162.8900 0073400  53.2400 307.4100 2.00568900195002
GPS BIIR-4
1 25933U 99055A   24045.50000000  .00000012  00000-0  10000-3 0  9988
2 25933  51.0500 282.7800 0046700 342.6700  17.2100 2.00571000195003
BEIDOU-3 M1
1 43539U 18062A   24045.50000000  .00000015  00000-0  10000-3 0  9987
2 43539  55.0200 175.6700 0014700  26.3400 333.7200 1.86234000050001
GALILEO 1
1 37846U 11060A   24045.50000000  .00000007  00000-0  10000-3 0  9986
2 37846  56.0400 297.1200 0003400 310.2300  49.7500 1.70475000090001
ASTRA 1N
1 36831U 10037A   24045.50000000  .00000010  00000-0  10000-3 0  9985
2 36831   0.0500  83.2100 0003200 129.8900 327.4300 1.00272000050001
INTELSAT 901
1 26824U 01024A   24045.50000000  .00000008  00000-0  10000-3 0  9984
2 26824   0.0300  52.4500 0003900  93.2100  15.6700 1.00274000040001
VANGUARD 1
1 00005U 58002B   24045.50000000  .00000024  00000-0  24300-3 0  9983
2 00005  34.2500 183.6700 1847200  87.4500 289.1200 10.84868000999999
"""


def _tle_to_dict(tle) -> dict:
    """Convert a parsed TLEData to a dict for database insertion."""
    return {
        "norad_id": tle.norad_id,
        "name": tle.name,
        "intl_designator": tle.intl_designator,
        "tle_line1": tle.tle_line1,
        "tle_line2": tle.tle_line2,
        "epoch": tle.epoch.isoformat(),
        "inclination": tle.inclination,
        "eccentricity": tle.eccentricity,
        "period_min": tle.period_min,
        "apogee_km": tle.apogee_km,
        "perigee_km": tle.perigee_km,
        "object_type": "PAYLOAD",
        "country_code": "",
        "launch_date": None,
        "decay_date": None,
        "rcs_size": "",
    }


def _parse_tle_text(text: str) -> list[dict]:
    """Parse 3-line TLE text into list of dicts."""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    results = []
    i = 0
    while i + 2 < len(lines):
        name_line = lines[i]
        line1 = lines[i + 1]
        line2 = lines[i + 2]
        if line1.startswith("1 ") and line2.startswith("2 "):
            try:
                tle = parse_tle(name_line, line1, line2)
                results.append(_tle_to_dict(tle))
            except (ValueError, IndexError) as e:
                logger.debug("Skipping invalid TLE: %s", e)
            i += 3
        else:
            i += 1
    return results


def fetch_tle_group(group: str = "active", timeout: float = 60.0) -> list[dict]:
    """Fetch TLE data for a satellite group from CelesTrak.

    Returns list of dicts compatible with SatelliteDB.upsert_satellite().
    """
    url = f"{BASE_URL}?GROUP={group}&FORMAT=tle"
    logger.info("Fetching TLEs from CelesTrak: group=%s", group)

    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("CelesTrak fetch failed: %s", e)
        return []

    text = resp.text.strip()
    if not text or "<html" in text.lower():
        logger.error("CelesTrak returned empty or HTML response for group=%s", group)
        return []

    results = _parse_tle_text(text)
    logger.info("Parsed %d satellites from CelesTrak group=%s", len(results), group)
    return results


def fetch_single_satellite(norad_id: int, timeout: float = 30.0) -> dict | None:
    """Fetch TLE for a single satellite by NORAD ID."""
    url = f"{BASE_URL}?CATNR={norad_id}&FORMAT=tle"
    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("CelesTrak single fetch failed: %s", e)
        return None

    text = resp.text.strip()
    if not text or "<html" in text.lower():
        return None

    results = _parse_tle_text(text)
    return results[0] if results else None


def get_demo_satellites() -> list[dict]:
    """Return bundled demo TLE data for offline/testing use.

    Includes 20 satellites: ISS, Tiangong, Starlinks, Hubble, NOAA, GPS, etc.
    """
    return _parse_tle_text(DEMO_TLES)
