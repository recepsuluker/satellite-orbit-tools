# 🛰️ Satellite Orbit Tools

[![CI](https://github.com/recepsuluker/satellite-orbit-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/recepsuluker/satellite-orbit-tools/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Track satellites in real time, screen them for close approaches, and predict
ground-station passes. You can use it as an operator dashboard, a REST/WebSocket
API, or a command-line tool. Everything is based on SGP4 propagation of public
TLE data from CelesTrak (and optionally Space-Track).

![Mission Control dashboard](docs/dashboard_preview.png)

## Features

- **Live tracking.** Animated 2D map, 3D globe and a sky-view (azimuth/elevation)
  radar for your ground station.
- **Conjunction screening.** Every pair of tracked satellites is propagated and
  checked for close approaches, with distance, relative velocity and a risk score.
- **Pass prediction.** AOS / max elevation / LOS for the next 24 hours from any
  location. Set the location by city name or coordinates.
- **Maneuver awareness.** Flags TLE mean-motion jumps as possible maneuvers. You
  can log planned burns and upload Space-Track CDM files for precision data.
- **Alerts.** E-mail, Slack and Telegram notifications for critical approaches,
  plus periodic status reports.
- **Catalog of 8,000+ active satellites.** Search by name or NORAD ID.
- **Three interfaces on one engine.** Mission Control dashboard, REST + WebSocket
  API with OpenAPI docs, and a Streamlit analytics app with CSV/HTML reports.

## Installation

Requires Python 3.10 or newer.

```bash
pip install git+https://github.com/recepsuluker/satellite-orbit-tools.git
```

Or with Docker, which starts all interfaces at once:

```bash
git clone https://github.com/recepsuluker/satellite-orbit-tools.git
cd satellite-orbit-tools
docker compose up -d
```

| Service | URL |
|---|---|
| Mission Control | http://localhost:8000 |
| REST API (interactive docs) | http://localhost:8001/docs |
| Analytics dashboard | http://localhost:8501 |

## Quick start

### Mission Control dashboard

```bash
satorbit mission-control
```

Open http://127.0.0.1:8000. The ISS and China's Tiangong station are tracked
by default. From the sidebar you can:

1. **Set your location** under *OPS LOCATION* (city search or lat/lon).
2. **Add satellites** under *ADD SATELLITE* (name or NORAD ID, e.g. `25544`).
3. Press **REFRESH SYSTEM** to redraw the maps.

The Guardian agent screens the tracked satellites for conjunctions every five
minutes. Results appear in the risk panel and in the Commander chat. Try
`where is ISS`, `next pass` or `collision`.

### Analytics dashboard and API

```bash
satorbit sync              # download TLEs from CelesTrak (or: satorbit sync --demo, offline)
satorbit dashboard         # Streamlit app on http://127.0.0.1:8501
satorbit api               # REST API, docs at http://127.0.0.1:8001/docs
```

Example API calls:

```bash
curl "http://127.0.0.1:8001/api/v1/satellites/?query=ISS"
curl "http://127.0.0.1:8001/api/v1/satellites/25544/position"
curl "http://127.0.0.1:8001/api/v1/visibility/passes/25544?lat=48.85&lon=2.35&duration_hours=24"
```

Run `satorbit --help` to see all commands.

## Configuration

All data (database, logs, Mission Control settings, caches) lives in one
directory: `~/.satorbit` by default. Set `SATORBIT_HOME` to move it.

**API and analytics dashboard:** use environment variables, or a `.env` file in
the directory you run from. See [`.env.example`](.env.example) for every option.

| Variable | Default | Purpose |
|---|---|---|
| `SPACETRACK_USERNAME` / `SPACETRACK_PASSWORD` | – | Optional, for Space-Track data ([free account](https://www.space-track.org/auth/createAccount)) |
| `COLLISION_THRESHOLD_KM` | `10` | Close-approach threshold |
| `GROUND_STATION_LAT` / `_LON` | Kennedy Space Center | Default observer |
| `REDIS_HOST` | `localhost` | Optional cache. Without Redis, results are just computed fresh |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8001` | API bind address |

**Mission Control:** edit `~/.satorbit/mission_control/config.json`. Most
settings are also editable in the UI.

```jsonc
{
  "settings": { "conjunction_threshold_km": 10.0, "prediction_days": 1 },
  "email":    { "smtp_server": "smtp.gmail.com", "smtp_port": 587,
                "sender_email": "you@gmail.com", "sender_password": "<app password>",
                "receiver_email": "ops@example.com" },
  "slack":    { "webhook_url": "https://hooks.slack.com/services/..." },
  "telegram": { "bot_token": "", "chat_id": "" }
}
```

Alert channels stay off until you fill them in. For Gmail, use an
[app password](https://support.google.com/accounts/answer/185833), not your
account password.

## How it works

TLEs are propagated with SGP4 in the TEME frame, rotated to ECEF and converted
to geodetic coordinates. Conjunction screening propagates each satellite on a
common time grid (1-minute steps by default) and reports the pairs whose
separation drops below the threshold. Pass prediction uses Skyfield's
rise/culminate/set search for the configured ground station.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the package layout, the
agents and the data directory.

## Limitations

> **This is an awareness and research tool, not a flight-safety system.**
> Public TLEs are accurate to roughly a kilometre near their epoch, and the
> error grows by kilometres per day. Screening on a 1-minute grid can miss the
> exact time of closest approach for fast crossings. Use CDMs from
> Space-Track / 18th SDS for any operational collision-avoidance decision.

## Development

```bash
git clone https://github.com/recepsuluker/satellite-orbit-tools.git
cd satellite-orbit-tools
pip install -e ".[dev]"
pytest                    # 89 tests, no network needed
ruff check . && ruff format --check .
```

The `examples/` folder has small stand-alone scripts that use the underlying
libraries directly. `rust_engine/` is an experimental parallel collision
kernel (PyO3 + Rayon) that isn't wired into the package yet.

See [CHANGELOG.md](CHANGELOG.md) for release history.

## License

[MIT](LICENSE) © Recep Suluker
