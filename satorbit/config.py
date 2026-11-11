"""Centralized configuration using pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

from satorbit.paths import data_home

DATA_DIR = data_home()


class Settings(BaseSettings):
    # Space-Track.org
    spacetrack_username: str = Field(default="", alias="SPACETRACK_USERNAME")
    spacetrack_password: str = Field(default="", alias="SPACETRACK_PASSWORD")

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # Database
    database_url: str = f"sqlite:///{DATA_DIR / 'satellites.db'}"

    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8001
    api_debug: bool = False

    # Streamlit
    streamlit_port: int = 8501
    streamlit_address: str = "127.0.0.1"

    # Logging
    log_level: str = "INFO"
    log_dir: str = str(DATA_DIR / "logs")

    # Collision detection
    collision_threshold_km: float = 10.0
    analysis_window_hours: int = 24
    propagation_step_minutes: int = 1

    # Ground station
    ground_station_lat: float = 28.5721
    ground_station_lon: float = -80.6480
    ground_station_elevation_m: float = 3.0
    ground_station_name: str = "Kennedy Space Center"

    # Cache TTL
    tle_cache_ttl: int = 3600
    analysis_cache_ttl: int = 1800

    model_config = {
        "env_file": ".env",  # read from the current working directory
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def db_path(self) -> Path:
        url = self.database_url
        if url.startswith("sqlite:///"):
            return Path(url.replace("sqlite:///", ""))
        return DATA_DIR / "satellites.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
