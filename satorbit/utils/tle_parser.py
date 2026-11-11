"""TLE (Two-Line Element) parsing utilities."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class TLEData:
    """Parsed TLE data."""

    name: str
    norad_id: int
    intl_designator: str
    epoch: datetime
    tle_line1: str
    tle_line2: str
    inclination: float
    raan: float
    eccentricity: float
    arg_perigee: float
    mean_anomaly: float
    mean_motion: float
    rev_number: int
    period_min: float
    apogee_km: float
    perigee_km: float


EARTH_RADIUS_KM = 6371.0
MU = 398600.4418  # km^3/s^2


def parse_tle(name: str, line1: str, line2: str) -> TLEData:
    """Parse a three-line TLE set into structured data."""
    name = name.strip()
    line1 = line1.strip()
    line2 = line2.strip()

    # Line 1 parsing
    norad_id = int(line1[2:7].strip())
    intl_designator = line1[9:17].strip()

    # Epoch
    epoch_year = int(line1[18:20])
    epoch_day = float(line1[20:32])
    year = 2000 + epoch_year if epoch_year < 57 else 1900 + epoch_year
    epoch = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=epoch_day - 1)

    # Line 2 parsing
    inclination = float(line2[8:16].strip())
    raan = float(line2[17:25].strip())
    eccentricity = float(f"0.{line2[26:33].strip()}")
    arg_perigee = float(line2[34:42].strip())
    mean_anomaly = float(line2[43:51].strip())
    mean_motion = float(line2[52:63].strip())
    rev_number = int(line2[63:68].strip()) if line2[63:68].strip() else 0

    # Derived values
    period_min = 1440.0 / mean_motion if mean_motion > 0 else 0
    # Semi-major axis from period
    period_sec = period_min * 60
    a = (MU * (period_sec / (2 * math.pi)) ** 2) ** (1 / 3)  # km
    apogee_km = a * (1 + eccentricity) - EARTH_RADIUS_KM
    perigee_km = a * (1 - eccentricity) - EARTH_RADIUS_KM

    return TLEData(
        name=name,
        norad_id=norad_id,
        intl_designator=intl_designator,
        epoch=epoch,
        tle_line1=line1,
        tle_line2=line2,
        inclination=inclination,
        raan=raan,
        eccentricity=eccentricity,
        arg_perigee=arg_perigee,
        mean_anomaly=mean_anomaly,
        mean_motion=mean_motion,
        rev_number=rev_number,
        period_min=round(period_min, 2),
        apogee_km=round(apogee_km, 2),
        perigee_km=round(perigee_km, 2),
    )


def parse_tle_text(text: str) -> list[TLEData]:
    """Parse multi-satellite TLE text (3-line format)."""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    results = []

    i = 0
    while i < len(lines):
        # Detect TLE format
        if i + 2 < len(lines) and lines[i + 1].startswith("1 ") and lines[i + 2].startswith("2 "):
            # 3-line format
            try:
                results.append(parse_tle(lines[i], lines[i + 1], lines[i + 2]))
            except (ValueError, IndexError):
                pass
            i += 3
        elif lines[i].startswith("1 ") and i + 1 < len(lines) and lines[i + 1].startswith("2 "):
            # 2-line format (no name)
            norad_id = lines[i][2:7].strip()
            try:
                results.append(parse_tle(f"SAT-{norad_id}", lines[i], lines[i + 1]))
            except (ValueError, IndexError):
                pass
            i += 2
        else:
            i += 1

    return results
