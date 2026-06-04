---
name: satellite-orbit-tools
description: |
  Project-specific guidance for the "Autonomous Multi-Agent Satellite Operations Platform"
  — a real-time, agent-driven satellite tracking, collision detection, and
  ground-station operations system built on Python 3.10+, FastAPI, and SGP4.
  The platform features a multi-agent architecture (Commander, Guardian, Notify,
  Auto-Sync, Mission Log) for autonomous monitoring and omni-channel alerting.
---

# Satellite Orbit Tools — Project Skill

This skill captures the conventions and workflows of the `satellite-orbit-tools`
repository so that any change made by an assistant fits cleanly into the existing
architecture, follows the established patterns, and does not regress the public API
or CLI.

## 1. What this project is

A modular, autonomous platform for satellite operations:

- **Autonomous Agent Architecture**: Multi-agent system (Commander, Guardian, Notify, Auto-Sync) handling background tasks and user interaction.
- **TLE Ingestion**: Auto-updating catalog via Auto-Sync Agent (every 6 hours).
- **Conjunction Analysis**: Real-time risk detection via Guardian Agent (every 30s) with distance sorting and risk assessment.
- **Omni-channel Alerts**: Notify Agent delivering critical alerts via Slack, Email, and Telegram with CSV report attachments.
- **Mission Terminal**: Live activity feed (Mission Log Agent) for system-wide transparency.
- **Orbit Propagation**: SGP4-based TEME→ECEF engine for real-time tracking.
- **Ground-station Ops**: City-based geocoding for station placement and pass prediction.

## 2. Repository map

```
satellite-orbit-tools/
├── cli.py                       # Operational CLI: init / sync / status / api / dashboard
├── conjunction_checker.py       # Legacy demo (Skyfield, 2 sats)            — do not extend
├── ground_pass_checker.py       # Legacy demo (Skyfield, 1 sat 1 station)   — do not extend
├── multi_conjunction_checker.py # Legacy demo (Space-Track + all-pairs CSV) — do not extend
├── satellite_track_2d.html      # Static 2D map viewer
├── satellite_track_3d.html      # Static 3D globe viewer
├── config.json                  # Runtime persisted settings (UI-managed)
├── requirements.txt / pyproject.toml
├── Dockerfile / docker-compose.yml
├── .github/workflows/ci.yml
├── .streamlit/config.toml
├── src/
│   ├── config.py                # pydantic-settings Settings + get_settings() (lru_cache)
│   ├── logging_config.py        # setup_logging() / get_logger("namespace")
│   ├── api/
│   │   ├── main.py              # FastAPI app + lifespan + CORS + router wiring
│   │   └── routes/
│   │       ├── satellites.py    # /api/v1/satellites
│   │       ├── collision.py     # /api/v1/collision
│   │       ├── visibility.py    # /api/v1/visibility
│   │       └── websocket_routes.py
│   ├── database/
│   │   ├── models.py            # SCHEMA_SQL, DEFAULT_STATIONS, initialize_database()
│   │   └── manager.py           # SatelliteDB context-manager: upsert, lookup, sync log
│   ├── engine/
│   │   ├── orbit_propagator.py  # SGP4 + TEME→ECEF, dataclasses SatellitePosition / PropagationResult
│   │   ├── collision_detector.py# ConjunctionEvent, CollisionAnalysis, analyze_collisions()
│   │   ├── visibility_calculator.py # GroundStation, PassEvent, calculate_passes()
│   │   └── cache.py             # In-memory / Redis-backed cache + get_cache_stats()
│   └── utils/
│       ├── celestrak_client.py  # GROUPS dict, fetch_tle_group(), get_demo_satellites()
│       ├── space_track_client.py# async SpaceTrackClient (login + tle_latest)
│       ├── tle_parser.py
│       └── export.py
├── frontend/
│   ├── app.py                   # Streamlit entry
│   └── pages/
│       ├── 01_dashboard.py
│       ├── 02_collision_analysis.py
│       ├── 03_visibility.py
│       ├── 04_3d_view.py
│       └── 05_reports.py
├── rust_engine/                 # Optional Rust acceleration (PyO3 stubs)
└── tests/                       # pytest suite (asyncio_mode = auto)
```

## 3. Domain conventions

These rules come from the existing code — keep new code consistent.

- **Coordinates**: SGP4 produces TEME km / km·s vectors. Always rotate to ECEF using
  `_gmst(jd, fr)` from `orbit_propagator.py` before converting to geodetic
  (lat, lon, alt). Do **not** mix Skyfield outputs with the SGP4 path inside
  `src/engine/`; the demos at the repo root are the only place Skyfield is used.
- **Distances** are in **kilometers** everywhere. Velocities are **km/s**. Times are
  always **timezone-aware UTC** (`datetime.now(timezone.utc)`).
- **NORAD IDs** are integers parsed from `tle_line2.split()[1]`. Treat 0 as
  "unknown" (set when TLE parsing fails).
- **Risk score** is a float in [0, 100], computed by
  `_calculate_risk_score(distance_km, relative_velocity_km_s)`. Categories:
  high ≥ 70, medium 30–70, low < 30. Re-use these thresholds; do not invent new ones.
- **Conjunction threshold** defaults to `Settings.collision_threshold_km` (10.0).
  Always plumb the threshold through; never hard-code in routes/UI.
- **Ground-station elevation** is stored in **meters**, but the geodetic conversion
  expects **kilometers** — divide by 1000 at the boundary
  (`station.elevation_m / 1000.0`), as in `visibility_calculator._calculate_look_angle`.
- **Pass minimum elevation** defaults to **10°**. The legacy `ground_pass_checker.py`
  uses Skyfield's `find_events`, the engine version uses sampled positions plus a
  state machine — keep the engine path.
- **Time stepping**: orbit propagation defaults to `step_minutes=1.0` over
  `duration_hours=24.0`. The conjunction matcher pairs positions by
  `timestamp.strftime("%Y%m%d%H%M%S")`, so any two satellites being compared **must
  be propagated on the same time grid**. Don't change one side's step without the
  other.

## 4. Configuration & secrets

All runtime config flows through `src.config.Settings` (pydantic-settings) and is
cached via `get_settings()`. Add new settings there with a sensible default; never
read environment variables directly inside engine / route code.

- `.env` is loaded automatically; `.env.example` documents available keys.
- Space-Track credentials: `SPACETRACK_USERNAME` / `SPACETRACK_PASSWORD`. If empty,
  `cli.py sync` falls back to CelesTrak automatically — preserve that fallback.
- The DB lives at `data/satellites.db` (SQLite, WAL mode). Do not bypass
  `database.models.get_connection()`; it sets `journal_mode=WAL`,
  `foreign_keys=ON`, and `busy_timeout=5000`.
- The dashboard's `config.json` at repo root is the **UI-managed** persisted store
  for ground-station + Telegram settings — separate from `Settings` / `.env`.

## 5. Coding conventions

- **Python 3.10+**, `from __future__ import annotations` at the top of new modules
  (matches existing files).
- **Dataclasses** for value objects (`SatellitePosition`, `ConjunctionEvent`,
  `PassEvent`, `GroundStation`, `PropagationResult`, `VisibilityResult`,
  `CollisionAnalysis`). Use `field(default_factory=list)` for collections.
- **Logging**: `from src.logging_config import get_logger; logger = get_logger("engine.<module>")`.
  Don't `print()` from inside `src/`; the CLI is allowed to print user-facing output.
- **Ruff** is the linter: `target-version = "py310"`, `line-length = 100`,
  selected rules `E, F, I, N, W`. Run `ruff check .` before committing.
- **Type hints** are expected on public functions. Module-level constants use
  `UPPER_SNAKE_CASE` (`EARTH_RADIUS_KM`, `GROUPS`, `SCHEMA_SQL`,
  `DEFAULT_STATIONS`).
- **No new top-level scripts.** New analysis features go inside `src/engine/`,
  exposed via `src/api/routes/` and / or invoked from `frontend/pages/`.

## 6. Common workflows

### 6.1 Add a new TLE source (or CelesTrak group)
1. Edit `src/utils/celestrak_client.py::GROUPS` — keep the `key: description`
   format; the CLI surfaces it via `cli.py sync --list-groups`.
2. If the source needs auth, model it on `src/utils/space_track_client.py`
   (async `httpx`, context-manager).
3. Update `cli.py::_sync_celestrak` or `_sync_spacetrack` only if the new source is
   a **provider**, not just a group.
4. Pipe results through `SatelliteDB.upsert_satellites_batch()` and
   `db.log_sync(added, updated, total_count, source=...)`.

### 6.2 Add a new collision-analysis feature
1. Extend the `ConjunctionEvent` dataclass in `collision_detector.py` for any new
   per-event fields. Keep the existing fields unchanged — `frontend/pages/02_…` and
   the routes deserialize them.
2. If you add a new aggregate, extend `CollisionAnalysis` and update the
   `high/medium/low` bucket logic only if the risk thresholds change.
3. Persist into `conjunction_events` (`src/database/models.py::SCHEMA_SQL`); add
   columns via a SQL migration committed to `models.py` and update `manager.py`.
4. Expose via `src/api/routes/collision.py`, then surface in
   `frontend/pages/02_collision_analysis.py`.

### 6.3 Add a ground station or visibility feature
1. Default seeds live in `DEFAULT_STATIONS` (`models.py`). User-added stations go
   through the API / UI, not seeds.
2. New per-pass fields → extend `PassEvent` and the `pass_predictions` table
   together.
3. The look-angle math (azimuth from north clockwise, elevation above horizon, slant
   range in km) lives in `_calculate_look_angle`. Reuse it; do not reimplement
   ENU conversions.

### 6.4 Add a new API endpoint
1. New router file in `src/api/routes/`, then `app.include_router(...)` in
   `src/api/main.py` with prefix `/api/v1/<thing>` and a `tags=[...]` entry.
2. Use Pydantic v2 models for request/response (project pin: `pydantic>=2.5`).
3. Cache hot reads with `src/engine/cache.py`; respect
   `Settings.tle_cache_ttl` (3600s) and `Settings.analysis_cache_ttl` (1800s).
4. Add tests under `tests/test_api.py`.

### 6.5 Add a CLI command
Add a `cmd_xxx(args)` function in `cli.py`, register a sub-parser inside `main()`,
and wire it into the `commands` dict. Keep CLI output plain text and avoid emojis
in operational messages (the existing commands use plain ASCII for log lines —
emojis are reserved for the legacy demo scripts).

### 6.6 Database changes
- Edit `SCHEMA_SQL` in `src/database/models.py`. All statements are
  `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`, so adding new tables
  / indexes is safe.
- For altering existing tables, add explicit `ALTER TABLE` statements **after**
  `executescript(SCHEMA_SQL)` inside `initialize_database()` and guard with
  `try/except sqlite3.OperationalError` (idempotent).
- Always go through `SatelliteDB` (`src/database/manager.py`) — it's a context
  manager with the right pragmas applied.

## 7. Testing & quality gates

- **Test runner**: `pytest` (configured in `pyproject.toml`,
  `asyncio_mode = "auto"`, `addopts = "-v --tb=short"`).
- **Run all tests**: `pytest` from the repo root after activating `venv/`.
- **Per-module**: `pytest tests/test_collision_detector.py -v`.
- **Lint**: `ruff check .` (and `ruff format .` if formatting drift is reported).
- **Smoke test the CLI** before shipping infra changes:
  `python cli.py init && python cli.py sync --demo && python cli.py status`.
- **Demo data** is bundled — `cli.py sync --demo` works fully offline. Use it in
  tests / CI rather than hitting CelesTrak or Space-Track.

## 8. Local run book

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# First-time setup
python cli.py init
python cli.py sync --demo        # offline, recommended for first run
python cli.py status

# Services
python cli.py api                # FastAPI on :8000  (docs at /docs, redoc at /redoc)
python cli.py dashboard          # Streamlit on :8501
```

Docker: `docker compose up` (see `docker-compose.yml` and `Dockerfile`). The
dashboard reads `config.json` for its UI-side ground-station and Telegram settings,
so persist that file in any deploy.

## 9. Things to avoid

- Do **not** add new logic to the legacy `*_checker.py` scripts at the repo root.
- Do **not** print credentials, TLE bodies, or PII in logs.
- Do **not** embed Space-Track credentials in source — they only come from
  `Settings.spacetrack_username` / `…_password` (env / `.env`).
- Do **not** call `requests` synchronously inside async paths; use `httpx` /
  `aiohttp` (already pinned).
- Do **not** widen the public dataclasses' field order without reviewing
  `frontend/` and `src/api/routes/` for positional consumers.
- Do **not** bypass `SatelliteDB` to write to the SQLite file directly.

## 10. Quick reference — key callables

| Purpose                          | Module / function                                                    |
|----------------------------------|----------------------------------------------------------------------|
| Settings (cached singleton)      | `src.config.get_settings()`                                          |
| Logger factory                   | `src.logging_config.get_logger("namespace")`                         |
| DB init + seed stations          | `src.database.models.initialize_database()`                          |
| DB context manager               | `src.database.manager.SatelliteDB`                                   |
| Single-satellite propagation     | `src.engine.orbit_propagator.propagate_satellite(...)`               |
| Batch propagation                | `src.engine.orbit_propagator.propagate_batch(...)`                   |
| Pairwise conjunction check       | `src.engine.collision_detector.check_conjunction_pair(...)`          |
| Full N-sat conjunction analysis  | `src.engine.collision_detector.analyze_collisions(...)`              |
| Pass prediction over a station   | `src.engine.visibility_calculator.calculate_passes(...)`             |
| CelesTrak group fetch            | `src.utils.celestrak_client.fetch_tle_group(group)`                  |
| Space-Track async client         | `src.utils.space_track_client.SpaceTrackClient`                      |
| Cache stats (used by /health)    | `src.engine.cache.get_cache_stats()`                                 |

## 11. Multi-Agent Architecture

The platform operates as a collective of specialized agents:

| Agent | Responsibility | Frequency | Output |
|-------|----------------|-----------|--------|
| **Commander** | User interface & chat logic | On-demand | Chat replies, Manual Maps |
| **Guardian** | Orbital collision hazard scanning | Every 30s (UI) | Conjunction Table, Banner |
| **Notify** | External reporting & emergency alerts | Every 30m / Instant | Email + CSV, Slack, Telegram |
| **Auto-Sync** | TLE sync + anomaly detection | Every 6 hours | Cached TLE catalog, MANEUVER DETECTED alerts |
| **Mission Log** | System-wide activity monitoring | Real-time | Live Dashboard Terminal |

All agents log their activity to the `system_logs` stream, accessible via `/api/logs`. Emergency alerts are triggered when `distance_km < 1.0`.

## 12. Maneuver Awareness Engine (v2.0)

The platform addresses the critical "Maneuver Blindness" problem — when SSN/Space-Track TLE data lags 6-24 hours behind actual orbital maneuvers.

### 12.1 Maneuver Planning (Step 1)
- **UI:** Sidebar → MANEUVER PLANNING panel. Select satellite, set UTC time, Delta-V (m/s), and burn duration (s).
- **Backend:** `POST /plan-maneuver` stores maneuver in `config.json`. `GET /api/maneuvers` lists all planned maneuvers. `POST /delete-maneuver/{id}` removes them.
- **Effect:** Conjunction risk analysis flags any satellite with an active maneuver as `HIGH (Maneuver)` uncertainty.

### 12.2 TLE Drift & Jump Analysis (Step 2)
- **Logic:** Auto-Sync Agent compares each satellite's incoming Mean Motion value against the previous snapshot stored in `config.json → satellites[].last_tle`.
- **Threshold:** A Mean Motion delta > 0.005 triggers an automatic `MANEUVER DETECTED` alert via Slack.
- **Purpose:** Detects maneuvers performed by other operators' satellites that affect your conjunction risk.

### 12.3 Uncertainty Visualization (Step 3)
- **Classification:** Each conjunction risk is tagged with an uncertainty level:
  - `NORMAL` — Standard TLE-based calculation, no anomalies.
  - `HIGH (Maneuver)` — One or both satellites have an active planned maneuver.
  - `PRECISION (CDM)` — Data sourced from a high-fidelity CDM file.
- **UI:** Maneuvering satellites are highlighted in orange. Uncertainty labels appear below each risk entry.

### 12.4 CDM Integration (Step 4)
- **Parser:** `utils.parse_cdm_xml()` extracts OBJECT_NAME, MISS_DISTANCE, and COLLISION_PROBABILITY from CCSDS-standard XML.
- **Upload:** Sidebar → PRECISION ANALYSIS (CDM) → Upload `.xml` file → `POST /upload-cdm`.
- **Display:** CDM-sourced risks appear in the conjunction table alongside TLE-based risks, tagged as `PRECISION (CDM)`.

### 12.5 Open SSA Monitor (Step 5)
- **Purpose:** Interface for monitoring external data from amateur observer networks (SeeSat-L, ExoAnalytic, LeoLabs).
- **UI:** Sidebar → OPEN SSA → SCAN FOR EXTERNAL ANOMALIES button. Currently simulates network scanning; designed for future API integration.

## 13. Notification Architecture

### 13.1 Scheduled Notifications (Every 30 Minutes)
- Guardian Agent scans `conjunction-warning.csv` every 5 minutes.
- Actual email/Slack dispatch occurs only on `iteration % 6 == 0` (every 30 min).
- If danger is found at the 30-min mark: URGENT alert with involved satellite names.
- If no danger: routine status report.

### 13.2 Manual Refresh Notifications
- When the user clicks "REFRESH SYSTEM", `NotifyAgent.send_manual_report()` is called.
- Sends a complete list of tracked satellite assets to both Gmail and Slack instantly.

### 13.3 Slack Message Format
Critical alerts follow the format:
```
🚨 CRITICAL SATELLITE ALERT 🚨
Detecting [N] high-risk conjunction events those [Sat1, Sat2, ...] satellites.
Please review the satellite-orbit-tools dashboard.
```
