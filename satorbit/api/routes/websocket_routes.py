"""WebSocket endpoints for real-time satellite tracking."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from satorbit.database.manager import SatelliteDB
from satorbit.engine.orbit_propagator import propagate_satellite
from satorbit.logging_config import get_logger

logger = get_logger("api.websocket")
router = APIRouter()


class ConnectionManager:
    """Manage active WebSocket connections."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connected. Active: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("WebSocket disconnected. Active: %d", len(self.active_connections))

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.active_connections.remove(conn)


manager = ConnectionManager()


@router.websocket("/ws/track")
async def websocket_track(websocket: WebSocket):
    """Real-time satellite position tracking via WebSocket.

    Client sends: {"norad_ids": [25544, 48274], "interval_sec": 5}
    Server streams: position updates every interval_sec seconds.
    """
    await manager.connect(websocket)
    try:
        # Wait for initial config
        data = await websocket.receive_json()
        norad_ids = data.get("norad_ids", [25544])
        interval = max(1, min(60, data.get("interval_sec", 5)))

        logger.info("Tracking %d satellites, interval=%ds", len(norad_ids), interval)

        # Load TLEs
        with SatelliteDB() as db:
            satellites = {}
            for nid in norad_ids:
                sat = db.get_satellite(nid)
                if sat:
                    satellites[nid] = sat

        if not satellites:
            await websocket.send_json({"error": "No valid satellites found"})
            return

        # Stream positions
        while True:
            positions = []
            now = datetime.now(timezone.utc)

            for nid, sat in satellites.items():
                result = propagate_satellite(
                    sat["tle_line1"],
                    sat["tle_line2"],
                    start_time=now,
                    duration_hours=0.01,
                    step_minutes=0.01,
                    name=sat["name"],
                )
                if result.positions:
                    pos = result.positions[0]
                    positions.append(
                        {
                            "norad_id": nid,
                            "name": sat["name"],
                            "lat": round(pos.latitude, 4),
                            "lon": round(pos.longitude, 4),
                            "alt_km": round(pos.altitude_km, 2),
                            "velocity_km_s": round(
                                (pos.vx_km_s**2 + pos.vy_km_s**2 + pos.vz_km_s**2) ** 0.5, 3
                            ),
                        }
                    )

            await websocket.send_json(
                {
                    "type": "position_update",
                    "timestamp": now.isoformat(),
                    "satellites": positions,
                }
            )

            await asyncio.sleep(interval)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        manager.disconnect(websocket)


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """Real-time collision alerts via WebSocket.

    Pushes alerts when new high-risk conjunctions are detected.
    """
    await manager.connect(websocket)
    try:
        last_check = ""
        while True:
            with SatelliteDB() as db:
                events = db.get_recent_conjunctions(10)

            high_risk = [e for e in events if (e.get("risk_score") or 0) >= 70]
            current_check = str([(e["id"], e["risk_score"]) for e in high_risk])

            if current_check != last_check and high_risk:
                await websocket.send_json(
                    {
                        "type": "collision_alert",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "alert_count": len(high_risk),
                        "events": [
                            {
                                "id": e["id"],
                                "sat_a": e.get("sat_a_name", f"NORAD-{e['satellite_a_id']}"),
                                "sat_b": e.get("sat_b_name", f"NORAD-{e['satellite_b_id']}"),
                                "distance_km": e["distance_km"],
                                "risk_score": e.get("risk_score", 0),
                                "event_time": e["event_time"],
                            }
                            for e in high_risk
                        ],
                    }
                )
                last_check = current_check

            await asyncio.sleep(30)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket alerts error: %s", e)
        manager.disconnect(websocket)
