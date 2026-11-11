"""File locations used by the Mission Control dashboard."""

from __future__ import annotations

import shutil
from pathlib import Path

from satorbit.paths import data_home

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
EXAMPLE_CONFIG = PACKAGE_DIR / "config.example.json"

HOME = data_home() / "mission_control"
CONFIG_FILE = HOME / "config.json"
TLE_DATA_DIR = HOME / "tle_cache"
MAPS_DIR = HOME / "maps"
CONJUNCTION_CSV = HOME / "conjunction-warning.csv"

for _directory in (HOME, TLE_DATA_DIR, MAPS_DIR):
    _directory.mkdir(parents=True, exist_ok=True)

if not CONFIG_FILE.exists():
    shutil.copyfile(EXAMPLE_CONFIG, CONFIG_FILE)
