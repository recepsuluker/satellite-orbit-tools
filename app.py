from fastapi import FastAPI, Request, Form, Body, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import json
import asyncio
import uuid
import pandas as pd
from datetime import datetime, timezone
from utils import (
    get_active_satellites, load_config, get_satellite_from_catalog,
    fetch_active_catalog, get_ground_station, get_upcoming_passes,
    send_telegram_alert, get_satellite_live_state, get_next_pass_summary,
    fetch_tle_by_norad_id,
)
from satellite_map_2d import generate_2d_map
from satellite_map_3d import generate_3d_map
from satellite_sky_view import generate_sky_view

app = FastAPI(title="Mission Control Dashboard")

# ---------------------------------------------------------------------------
# MISSION LOG SYSTEM
# ---------------------------------------------------------------------------
system_logs = []

def log_event(message, level="INFO"):
    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {level}: {message}"
    system_logs.append(log_entry)
    if len(system_logs) > 50: # Son 50 logu tutalım
        system_logs.pop(0)
    print(log_entry)

log_event("Mission Control System Initialized", "SYSTEM")

@app.get("/api/logs")
async def get_logs():
    return {"logs": system_logs}

@app.get("/passes")
async def get_all_passes():
    """Tüm takibe alınan uydular için önümüzdeki geçişleri hesaplar."""
    satellites, _ = get_active_satellites()
    station, _ = get_ground_station()
    
    all_passes = []
    for sat in satellites:
        p = get_upcoming_passes(sat, station)
        all_passes.extend(p)
    
    # Zaman sırasına göre diz
    all_passes.sort(key=lambda x: x['aos']['datetime'])
    
    # datetime objelerini string'e çevir (JSON serileştirme için)
    for p in all_passes:
        p['aos']['datetime'] = p['aos']['datetime'].isoformat()
        p['max']['datetime'] = p['max']['datetime'].isoformat()
        p['los']['datetime'] = p['los']['datetime'].isoformat()
        
    return all_passes

# Statik dosyalar ve şablonlar
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

CONFIG_FILE = "config.json"

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    config = load_config()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "satellites": config.get("satellites", []),
        "ground_station": config.get("ground_station", {}),
        "telegram": config.get("telegram", {})
    })

@app.post("/update-telegram")
async def update_telegram(bot_token: str = Form(...), chat_id: str = Form(...)):
    config = load_config()
    config['telegram'] = {"bot_token": bot_token, "chat_id": chat_id}
    save_config(config)
    return {"status": "success"}

@app.post("/test-telegram")
async def test_telegram():
    success = send_telegram_alert("🚀 <b>Mission Control Online!</b> \nSatellite Tracking System is linked to Telegram.")
    return {"status": "success" if success else "failed"}

@app.get("/search")
async def search_satellites(q: str):
    """Katalogda arama yapar ve ilk 10 sonucu döner."""
    catalog = fetch_active_catalog()
    results = []
    for i in range(0, len(catalog) - 2, 3):
        name = catalog[i].strip()
        line2 = catalog[i+2]
        norad_id = line2.split()[1]
        if q.upper() in name.upper() or q == norad_id:
            results.append({"name": name, "norad_id": norad_id})
        if len(results) >= 10: break
    return results

@app.post("/add-satellite")
async def add_satellite(name: str = Form(...), norad_id: str = Form(...)):
    config = load_config()
    if not any(s['norad_id'] == norad_id for s in config['satellites']):
        config['satellites'].append({"name": name, "norad_id": norad_id})
        save_config(config)
    return {"status": "success"}

@app.post("/plan-maneuver")
async def plan_maneuver(norad_id: str = Form(...), time: str = Form(...), dv: float = Form(...), duration: int = Form(...)):
    config = load_config()
    if 'maneuvers' not in config: config['maneuvers'] = []
    
    import uuid
    maneuver = {
        "id": str(uuid.uuid4()),
        "norad_id": norad_id,
        "time": time,
        "dv_ms": dv,
        "duration_s": duration,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    config['maneuvers'].append(maneuver)
    save_config(config)
    log_event(f"Maneuver Scheduled for NORAD {norad_id} at {time} (DV: {dv}m/s)", "ALERT")
    return {"status": "success"}

@app.post("/upload-cdm")
async def upload_cdm(file: UploadFile = File(...)):
    content = await file.read()
    from utils import parse_cdm_xml
    data = parse_cdm_xml(content)
    
    if data:
        config = load_config()
        if 'precision_risks' not in config: config['precision_risks'] = []
        data['id'] = str(uuid.uuid4())
        config['precision_risks'].append(data)
        save_config(config)
        log_event(f"CDM Imported: {data['satellite_1']} vs {data['satellite_2']} (Pc: {data['probability']})", "SUCCESS")
        return {"status": "success", "data": data}
    return {"status": "failed", "error": "Could not parse CDM file"}

@app.get("/api/maneuvers")
async def get_maneuvers():
    config = load_config()
    return config.get('maneuvers', [])

@app.post("/delete-maneuver/{man_id}")
async def delete_maneuver(man_id: str):
    config = load_config()
    if 'maneuvers' in config:
        config['maneuvers'] = [m for m in config['maneuvers'] if m['id'] != man_id]
        save_config(config)
    return {"status": "success"}

@app.post("/remove-satellite")
async def remove_satellite(norad_id: str = Form(...)):
    log_event(f"Commander requested removal of satellite ID: {norad_id}", "USER")
    config = load_config()
    # Hem string hem int karşılaştırması yapabilmek için her iki tarafı da string'e çeviriyoruz
    config['satellites'] = [s for s in config['satellites'] if str(s['norad_id']) != str(norad_id)]
    save_config(config)
    return {"status": "success"}

@app.post("/update-location")
async def update_location(name: str = Form(...), lat: float = Form(...), lon: float = Form(...), ele: float = Form(...)):
    config = load_config()
    config['ground_station'] = {"name": name, "latitude": lat, "longitude": lon, "elevation_m": ele}
    save_config(config)
    log_event(f"Ops Location updated: {name} ({lat}, {lon})", "SUCCESS")
    return {"status": "success"}

@app.post("/geocode")
async def geocode(city: str = Body(..., embed=True)):
    """Şehir isminden koordinat bulur (Nominatim API)."""
    import requests
    url = f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1"
    headers = {"User-Agent": "SatelliteTracker/1.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        data = resp.json()
        if data:
            return {
                "lat": float(data[0]["lat"]),
                "lon": float(data[0]["lon"]),
                "display_name": data[0]["display_name"].split(",")[0]
            }
        return {"error": "City not found"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/refresh-maps")
async def refresh_maps():
    log_event("Commander requested manual map synchronization.", "USER")
    config = load_config()
    
    # Anlık rapor gönder
    try:
        agent = NotifyAgent()
        agent.send_manual_report(config.get('satellites', []))
        log_event("Notify Agent: Manual status report sent to Gmail & Slack.", "INFO")
    except Exception as e:
        log_event(f"Notify Agent Sync Error: {e}", "WARNING")

    success_2d = generate_2d_map("static/satellite_track_2d.html")
    success_3d = generate_3d_map("static/satellite_track_3d.html")
    success_sky = generate_sky_view("static/satellite_sky_view.html")
    if success_2d and success_3d and success_sky:
        log_event("Global map engines updated.", "SUCCESS")
    return {"status": "success" if (success_2d and success_3d and success_sky) else "failed"}

@app.get("/conjunctions")
async def get_conjunctions():
    """Çarpışma risklerini analiz eder ve belirsizlik + CDM verilerini birleştirir."""
    results = []
    config = load_config()
    
    # 1. TLE Bazlı Riskler (CSV'den)
    if os.path.exists("conjunction-warning.csv"):
        try:
            df = pd.read_csv("conjunction-warning.csv")
            df = df.sort_values('distance_km').head(15)
            maneuvers = config.get('maneuvers', [])
            active_man_sats = [m['norad_id'] for m in maneuvers]

            for _, row in df.iterrows():
                is_maneuvering = str(row['norad_1']) in active_man_sats or str(row['norad_2']) in active_man_sats
                results.append({
                    "satellite_1": row['satellite_1'],
                    "satellite_2": row['satellite_2'],
                    "distance_km": float(row['distance_km']),
                    "uncertainty": "HIGH (Maneuver)" if is_maneuvering else "NORMAL",
                    "is_maneuvering": is_maneuvering,
                    "source": "TLE Analysis"
                })
        except Exception: pass

    # 2. CDM Bazlı Hassas Riskler (Config'den)
    p_risks = config.get('precision_risks', [])
    for pr in p_risks:
        results.append({
            "satellite_1": pr['satellite_1'],
            "satellite_2": pr['satellite_2'],
            "distance_km": pr['distance_km'],
            "uncertainty": "PRECISION (CDM)",
            "is_maneuvering": False,
            "is_precision": True,
            "probability": pr.get('probability', 'N/A'),
            "source": "CDM"
        })
    
    # Mesafeye göre tekrar sırala
    return sorted(results, key=lambda x: x['distance_km'])


# ---------------------------------------------------------------------------
# LIVE DATA: tracked satellites with current positions
# ---------------------------------------------------------------------------
@app.get("/api/satellites")
async def api_satellites():
    """Şu anda takip edilen uyduların canlı durumunu döner.

    Her uydu için: lat/lon/altitude/velocity, ufuk üstünde olup olmadığı,
    (varsa) yer istasyonundan az/el/range, ve sıradaki geçiş özeti.
    """
    sat_objects, config = get_active_satellites()
    station, gs_info = get_ground_station()
    configured = config.get("satellites", [])

    # NORAD ID -> obje
    by_id = {sat.model.satnum: sat for sat in sat_objects}

    items = []
    for entry in configured:
        norad_id = str(entry.get("norad_id"))
        sat_obj = None
        # match by integer satnum
        try:
            sat_obj = by_id.get(int(norad_id))
        except (TypeError, ValueError):
            sat_obj = None

        item = {
            "norad_id": norad_id,
            "name": entry.get("name", "UNKNOWN"),
            "tle_loaded": sat_obj is not None,
        }
        if sat_obj is not None:
            try:
                item["live"] = get_satellite_live_state(sat_obj, station)
            except Exception as e:
                item["live"] = None
                item["error"] = f"position: {e}"
            try:
                np = get_next_pass_summary(sat_obj, station, hours=24)
                item["next_pass"] = np
            except Exception:
                item["next_pass"] = None
        else:
            item["live"] = None
            item["next_pass"] = None
        items.append(item)

    return {
        "ground_station": gs_info,
        "satellites": items,
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
    }


# ---------------------------------------------------------------------------
# AGENT CHAT: live, intent-based replies
# ---------------------------------------------------------------------------
def _format_live(sat_item: dict) -> str:
    live = sat_item.get("live") or {}
    if not live:
        return f"<b>{sat_item['name']}</b> (NORAD {sat_item['norad_id']}) — TLE not loaded yet."
    horizon = "above horizon" if live.get("above_horizon") else "below horizon"
    parts = [
        f"<b>{sat_item['name']}</b> (NORAD {sat_item['norad_id']})",
        f"lat {live['latitude']}°, lon {live['longitude']}°",
        f"alt {live['altitude_km']} km",
    ]
    if live.get("velocity_km_s") is not None:
        parts.append(f"v {live['velocity_km_s']} km/s")
    if "elevation" in live:
        parts.append(f"el {live['elevation']}° / az {live['azimuth']}° ({horizon})")
    return " · ".join(parts)


def _build_chat_reply(message: str) -> str:
    """Çok hafif niyet (intent) çıkarımı + canlı veriden cevap."""
    text = (message or "").strip().lower()
    if not text:
        return "Awaiting your command, Commander."

    # canlı veriyi al
    sat_objects, config = get_active_satellites()
    station, gs_info = get_ground_station()
    configured = config.get("satellites", [])

    # NORAD-id → live-data dict
    live_items = []
    by_id = {sat.model.satnum: sat for sat in sat_objects}
    for entry in configured:
        norad_id = str(entry.get("norad_id"))
        sat_obj = by_id.get(int(norad_id)) if norad_id.isdigit() else None
        item = {"norad_id": norad_id, "name": entry.get("name", "UNKNOWN"), "live": None, "next_pass": None}
        if sat_obj is not None:
            try:
                item["live"] = get_satellite_live_state(sat_obj, station)
            except Exception:
                pass
            try:
                item["next_pass"] = get_next_pass_summary(sat_obj, station, hours=24)
            except Exception:
                pass
        live_items.append(item)

    # ---- intent: help -------------------------------------------------------
    if any(k in text for k in ["help", "yardim", "yardım", "what can you do", "commands"]):
        return (
            "I can answer with live orbital data:<br>"
            "• <b>list / status</b> — currently tracked satellites<br>"
            "• <b>where is &lt;name&gt;</b> — current lat/lon/alt<br>"
            "• <b>position / pos</b> — positions of all tracked sats<br>"
            "• <b>next pass</b> — upcoming passes over the ground station<br>"
            "• <b>collision / risk</b> — scan for potential orbital hazards<br>"
            "• <b>visible / overhead</b> — which sats are above the horizon<br>"
            "• <b>find &lt;query&gt;</b> — search Celestrak for a satellite by name/ID<br>"
            "• <b>station</b> — current ground station info"
        )

    # ---- intent: find / search Celestrak catalog ----------------------------
    if any(k in text for k in ["find", "search", "look up", "lookup", "ara", "bul"]):
        # extract query after the verb
        query = text
        for verb in ["find the", "find a", "find", "search for", "search", "look up", "lookup", "ara", "bul"]:
            if verb in query:
                query = query.split(verb, 1)[1].strip()
                break
        # strip filler words
        for noise in [" satellite id", " satellite", " satellites", " id", " norad"]:
            query = query.replace(noise, "")
        query = query.strip(" ?.,'\"-")
        if not query:
            return "Please tell me what to search for, e.g. <i>find starlink-30000</i> or <i>find plan-s</i>."

        # catalog search
        try:
            catalog = fetch_active_catalog()
        except Exception:
            catalog = []
        results = []
        q_up = query.upper()
        for i in range(0, len(catalog) - 2, 3):
            name = catalog[i].strip()
            try:
                norad_id = catalog[i + 2].split()[1]
            except Exception:
                continue
            if q_up in name.upper() or query == norad_id:
                results.append((name, norad_id))
                if len(results) >= 8:
                    break

        if not results:
            return (
                f"No matches in the active Celestrak catalog for <i>{query}</i>. "
                "Try the exact name (e.g. <i>find connecta</i>) or a NORAD ID."
            )
        lines = [f"Found <b>{len(results)}</b> match(es) for <i>{query}</i>:"]
        for name, nid in results:
            lines.append(f"• <b>{name}</b> <span style='color:#8b949e'>(NORAD {nid})</span>")
        lines.append(
            "<br><span style='color:#8b949e;font-size:0.78em;'>"
            "Use the sidebar 'ADD SATELLITE' input to start tracking one.</span>"
        )
        return "<br>".join(lines)

    # ---- intent: ground station --------------------------------------------
    if any(k in text for k in ["station", "ground station", "istasyon", "yer istasyon"]):
        return (
            f"Ground station <b>{gs_info.get('name')}</b> · "
            f"lat {gs_info.get('latitude')}°, lon {gs_info.get('longitude')}°, "
            f"elev {gs_info.get('elevation_m')} m."
        )

    # ---- intent: list / status ---------------------------------------------
    if any(k in text for k in ["list", "status", "constellation", "tracked", "monitor"]):
        if not live_items:
            return "No satellites tracked yet. Use the sidebar to add one."
        lines = [f"Tracking <b>{len(live_items)}</b> asset(s):"]
        for s in live_items:
            tag = "✅" if s["live"] else "⚠️ TLE missing"
            lines.append(f"{tag} {s['name']} <span style='color:#8b949e'>(NORAD {s['norad_id']})</span>")
        return "<br>".join(lines)

    # ---- intent: visible / overhead ----------------------------------------
    if any(k in text for k in ["visible", "overhead", "above", "horizon"]):
        visible = [s for s in live_items if s["live"] and s["live"].get("above_horizon")]
        if not visible:
            return "No tracked satellites are above the horizon right now."
        lines = ["Above the horizon now:"]
        for s in visible:
            lines.append("• " + _format_live(s))
        return "<br>".join(lines)

    # ---- intent: next pass --------------------------------------------------
    if any(k in text for k in ["next pass", "pass", "rise", "aos", "geçiş", "gecis"]):
        with_passes = [s for s in live_items if s.get("next_pass")]
        if not with_passes:
            return "No upcoming passes in the next 24 hours."
        # sort by soonest
        with_passes.sort(key=lambda s: s["next_pass"]["minutes_until"])
        lines = ["Upcoming passes:"]
        for s in with_passes[:5]:
            np = s["next_pass"]
            lines.append(
                f"• <b>{s['name']}</b> in {np['minutes_until']} min "
                f"(AOS {np['aos_time']} UTC · max el {np['max_elevation']}° · {np['duration_min']} min)"
            )
        return "<br>".join(lines)

    # ---- intent: where is <name> -------------------------------------------
    # find a satellite name that appears in the message
    matched = None
    for s in live_items:
        if s["name"].lower() in text or s["norad_id"] in text:
            matched = s
            break
    if matched and any(k in text for k in ["where", "position", "pos", "konum", "nerede", "lat", "altitude"]):
        return _format_live(matched)
    if matched:
        # if user just typed a sat name without verb, still report position
        return _format_live(matched)

    # ---- intent: position (all) --------------------------------------------
    if any(k in text for k in ["position", "pos", "where", "konum"]):
        if not live_items:
            return "No satellites tracked yet."
        lines = ["Current positions:"]
        for s in live_items:
            lines.append("• " + _format_live(s))
        return "<br>".join(lines)

    # ---- intent: collision / conjunction / danger --------------------------
    if any(k in text for k in ["collision", "conjunction", "danger", "risk", "hazard", "carpisma", "tehlike", "risk"]):
        csv_path = "conjunction-warning.csv"
        if not os.path.exists(csv_path):
            return "No conjunction data available. Analysis might be pending."
        
        try:
            import pandas as pd
            df = pd.read_csv(csv_path)
            # Find the most critical risk
            critical = df.sort_values(by="distance_km").head(5)
            if critical.empty:
                return "Scanning... No immediate collision hazards detected in the current constellation."
            
            lines = ["🚨 <b>COLLISION RISK ASSESSMENT</b> 🚨"]
            for _, row in critical.iterrows():
                dist = row['distance_km']
                severity = "🔴 CRITICAL" if dist < 1.0 else ("🟡 MEDIUM" if dist < 5.0 else "⚪ LOW")
                lines.append(
                    f"• {severity}: <b>{row['satellite_1']}</b> ↔ <b>{row['satellite_2']}</b> "
                    f"at <b>{dist:.2f} km</b> (UTC {row['time_utc']})"
                )
            
            if (critical['distance_km'] < 1.0).any():
                lines.append("<br><span style='color:#ff4d4d'>⚠️ WARNING: Multiple high-risk close approaches detected. Monitoring closely.</span>")
            else:
                lines.append("<br>System reports nominal safety margins for the rest of the constellation.")
            
            return "<br>".join(lines)
        except Exception as e:
            return f"I encountered an error analyzing collision data: {e}"

    # ---- fallback -----------------------------------------------------------
    return (
        f"I didn't catch that, Commander. Try: <i>list</i>, <i>where is ISS</i>, "
        f"<i>next pass</i>, <i>visible</i>, or <i>help</i>."
    )


@app.post("/chat")
async def chat(payload: dict = Body(...)):
    message = (payload or {}).get("message", "")
    reply = _build_chat_reply(message)
    return {"reply": reply, "computed_at_utc": datetime.now(timezone.utc).isoformat()}

# ---------------------------------------------------------------------------
# BACKGROUND AGENTS
# ---------------------------------------------------------------------------
import asyncio
from notify_agent import NotifyAgent

async def notify_agent_task():
    """Notify Agent'ı arka planda çalıştıran döngü."""
    agent = NotifyAgent()
    iteration = 0
    while True:
        try:
            # Her 5 dakikada bir tehlike kontrolü yap (conjunction-warning.csv'yi tara)
            # Ancak bildirimleri (Tehlike veya Rutin) sadece 30 dakikada bir (iteration % 6) gönder
            log_event("Guardian Agent: Scanning for orbital hazards...", "SCAN")
            danger_found, count, involved = agent._has_danger()
            
            if iteration % 6 == 0:
                if danger_found:
                    log_event(f"Notify Agent: CRITICAL HAZARD! Sending 30-min interval alert ({count} events).", "ALERT")
                    agent.send_email_report(is_urgent=True)
                    agent.send_slack_alert(count, involved)
                else:
                    log_event("Notify Agent: Sending routine 30-minute status report.", "INFO")
                    agent.send_email_report(is_urgent=False)
            
            iteration += 1
        except Exception as e:
            print(f"⚠️ NotifyAgent Task Error: {e}")
            
        await asyncio.sleep(300) # 5 dakika bekle

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(notify_agent_task())
    asyncio.create_task(auto_sync_task())

async def auto_sync_task():
    """TLE verilerini 6 saatte bir otonom güncelleyen ajan."""
    while True:
        try:
            log_event("Auto-Sync Agent: Checking for TLE updates and maneuvers...", "SCAN")
            config = load_config()
            sats = config.get('satellites', [])
            maneuvers_detected = []

            for s in sats:
                # Eski TLE'yi sakla
                old_tle = s.get('last_tle', {})
                new_tle_str = fetch_tle_by_norad_id(s['norad_id'])
                
                if new_tle_str and len(new_tle_str) == 3:
                    # Basit bir "Mean Motion" kıyaslaması (Line 2, characters 52-63)
                    new_mm = float(new_tle_str[2][52:63])
                    s['last_tle'] = {"line2": new_tle_str[2], "mean_motion": new_mm}
                    
                    if old_tle and 'mean_motion' in old_tle:
                        diff = abs(new_mm - old_tle['mean_motion'])
                        if diff > 0.005: # Manevra eşiği (Hızda ciddi değişim)
                            maneuvers_detected.append(s['name'])
                            log_event(f"⚠️ ANOMALY DETECTED: {s['name']} (Jump: {diff:.5f}) - Potential Maneuver!", "ALERT")
            
            save_config(config)
            
            if maneuvers_detected:
                # Notify Agent'ı tetikle
                from notify_agent import NotifyAgent
                na = NotifyAgent()
                na.send_slack_alert(len(maneuvers_detected), involved_sats=maneuvers_detected)
            
            log_event("Auto-Sync Agent: Cycle complete. Orbit data synchronized.", "SUCCESS")
        except Exception as e:
            log_event(f"Auto-Sync Agent Error: {e}", "ERROR")
        
        await asyncio.sleep(21600) # 6 saat bekle

if __name__ == "__main__":
    import uvicorn
    fetch_active_catalog()  # Uygulama açılırken kataloğu hazırla
    # reload=True → dosya değişiklikleri otomatik yeniden yüklenir.
    # Module-string biçimi ('app:app') reload için zorunlu.
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
