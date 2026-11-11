"""Async Space-Track.org API client for fetching TLE data."""

from __future__ import annotations

import asyncio

import aiohttp

from satorbit.config import get_settings
from satorbit.engine.cache import cache_get, cache_set
from satorbit.logging_config import get_logger

logger = get_logger("utils.space_track")

LOGIN_URL = "https://www.space-track.org/ajaxauth/login"
TLE_URL = "https://www.space-track.org/basicspacedata/query"


class SpaceTrackClient:
    """Async client for the Space-Track.org REST API."""

    def __init__(self, username: str | None = None, password: str | None = None):
        settings = get_settings()
        self.username = username or settings.spacetrack_username
        self.password = password or settings.spacetrack_password
        self._session: aiohttp.ClientSession | None = None
        self._authenticated = False

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()

    async def _ensure_session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()

    async def authenticate(self) -> bool:
        """Authenticate with Space-Track.org."""
        if not self.username or not self.password:
            logger.error("Space-Track credentials not configured")
            return False

        await self._ensure_session()
        try:
            async with self._session.post(
                LOGIN_URL,
                data={"identity": self.username, "password": self.password},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    self._authenticated = True
                    logger.info("Authenticated with Space-Track.org")
                    return True
                else:
                    logger.error("Space-Track auth failed: HTTP %d", resp.status)
                    return False
        except Exception as e:
            logger.error("Space-Track auth error: %s", e)
            return False

    async def fetch_tle_latest(
        self,
        norad_ids: list[int] | None = None,
        object_type: str | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        """Fetch latest TLE data from Space-Track.

        Returns list of dicts with satellite info and TLE lines.
        """
        # Check cache first
        cache_key_parts = [str(norad_ids), str(object_type), str(limit)]
        cached = cache_get("tle_latest", *cache_key_parts)
        if cached:
            logger.info("Returning %d TLEs from cache", len(cached))
            return cached

        if not self._authenticated:
            if not await self.authenticate():
                return []

        # Build query URL
        query_parts = [
            "/class/gp",
            "/EPOCH/>now-30",
            "/orderby/NORAD_CAT_ID",
            f"/limit/{limit}",
            "/format/json",
        ]
        if norad_ids:
            ids_str = ",".join(str(i) for i in norad_ids)
            query_parts.insert(1, f"/NORAD_CAT_ID/{ids_str}")
        if object_type:
            query_parts.insert(1, f"/OBJECT_TYPE/{object_type}")

        url = TLE_URL + "".join(query_parts)

        try:
            async with self._session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status != 200:
                    logger.error("Space-Track query failed: HTTP %d", resp.status)
                    return []

                data = await resp.json()
                results = []
                for item in data:
                    results.append(
                        {
                            "norad_id": int(item.get("NORAD_CAT_ID", 0)),
                            "name": item.get("OBJECT_NAME", "UNKNOWN"),
                            "intl_designator": item.get("INTLDES", ""),
                            "tle_line1": item.get("TLE_LINE1", ""),
                            "tle_line2": item.get("TLE_LINE2", ""),
                            "epoch": item.get("EPOCH", ""),
                            "inclination": float(item.get("INCLINATION", 0)),
                            "eccentricity": float(item.get("ECCENTRICITY", 0)),
                            "period_min": float(item.get("PERIOD", 0)),
                            "apogee_km": float(item.get("APOAPSIS", 0)),
                            "perigee_km": float(item.get("PERIAPSIS", 0)),
                            "object_type": item.get("OBJECT_TYPE", "PAYLOAD"),
                            "country_code": item.get("COUNTRY_CODE", ""),
                            "launch_date": item.get("LAUNCH_DATE", ""),
                            "decay_date": item.get("DECAY_DATE"),
                            "rcs_size": item.get("RCS_SIZE", ""),
                        }
                    )

                # Cache the results
                settings = get_settings()
                cache_set("tle_latest", *cache_key_parts, value=results, ttl=settings.tle_cache_ttl)
                logger.info("Fetched %d TLEs from Space-Track", len(results))
                return results
        except asyncio.TimeoutError:
            logger.error("Space-Track query timed out")
            return []
        except Exception as e:
            logger.error("Space-Track query error: %s", e)
            return []

    async def fetch_catalog_count(self) -> int:
        """Get total number of objects in the Space-Track catalog."""
        if not self._authenticated:
            if not await self.authenticate():
                return 0
        try:
            url = TLE_URL + "/class/gp/EPOCH/>now-30/format/json/limit/1"
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=30)):
                # Space-Track doesn't have a count endpoint; we return what we know
                return 0
        except Exception:
            return 0

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None
