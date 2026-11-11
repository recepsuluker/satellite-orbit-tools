# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [2.1.0] - 2026-11-11

Packaging and production-readiness release.

### Added
- `satorbit` command-line entry point (`pip install .`), with a `mission-control`
  subcommand alongside `init`, `sync`, `status`, `api` and `dashboard`.
- Guardian agent now **computes** conjunctions between tracked satellites with
  the SGP4 engine (`satorbit/mission_control/guardian.py`). Before, it only read
  a CSV that a separate script had to produce.
- Single data directory (`SATORBIT_HOME`, default `~/.satorbit`) for the
  database, logs, Mission Control config, TLE cache and generated maps.
- Placeholder map pages, so the dashboard iframes are never blank on first start.
- Mission Control test suite (10 tests). Total: 89 tests.
- Non-root Docker image with health check; Compose stack running all three
  interfaces plus Redis.
- CI: lint, tests on Python 3.10–3.12, wheel build and clean install, Docker
  build and smoke test, Rust engine check.
- MIT `LICENSE`, this changelog, `docs/ARCHITECTURE.md`.

### Fixed
- `pip install .` failed: invalid build backend in `pyproject.toml`.
- Mission Control home page crashed with HTTP 500 on current Starlette
  (`TemplateResponse` signature).
- Searching the catalog by NORAD ID could return a satellite whose *name*
  contained the digits.
- Missing runtime dependencies (`jinja2`, `python-multipart`, `requests`).
- The example config shipped placeholder SMTP/Slack credentials that triggered
  failing login attempts every 30 minutes.
- The Streamlit theme was lost unless the dashboard ran from the repository root.
- Deprecated `datetime.utcnow()` and FastAPI `on_event` usage.

### Changed
- The `src` package was renamed to `satorbit`. The Mission Control app moved
  into `satorbit/mission_control/`, the Streamlit app into `satorbit/dashboard/`.
- Stand-alone scripts moved to `examples/`. Space-Track credentials are read
  from environment variables instead of being hard-coded.
- The API and dashboard bind to `127.0.0.1` by default. Docker binds to `0.0.0.0`.
- Generated files (CSV, HTML maps, 2.5 MB TLE cache) are no longer committed.

## [2.0.0] - 2026-05-05

### Added
- Maneuver Awareness Engine: maneuver planning, TLE mean-motion jump detection,
  uncertainty tags, CDM (XML) upload, Open SSA monitor.
- 30-minute notification cycle.

## [1.5.0] - 2026-03-19

### Added
- Multi-agent architecture (Commander, Guardian, Notify, Auto-Sync, Mission Log).
- Gmail, Slack and Telegram alerting. City geocoding. Mission terminal.
- CLI, CelesTrak client, live TLE sync, FastAPI backend, Streamlit dashboard.

## [1.0.0] - 2025-04-06

### Added
- Core tracking, 2D/3D/sky-view maps, pass prediction, conjunction analysis.
