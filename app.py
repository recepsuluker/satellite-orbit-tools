from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
import os
import json
from utils import (
    get_active_satellites, load_config, get_satellite_from_catalog, 
    fetch_active_catalog, get_ground_station, get_upcoming_passes,
    send_telegram_alert
)
from satellite_map_2d import generate_2d_map
from satellite_map_3d import generate_3d_map
from satellite_sky_view import generate_sky_view

app = FastAPI(title="Mission Control Dashboard")

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
templates = Environment(loader=FileSystemLoader("templates"))

CONFIG_FILE = "config.json"

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    config = load_config()
    template = templates.get_template("index.html")
    content = template.render(
        satellites=config.get("satellites", []),
        ground_station=config.get("ground_station", {}),
        telegram=config.get("telegram", {})
    )
    return HTMLResponse(content=content)

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

@app.post("/remove-satellite")
async def remove_satellite(norad_id: str = Form(...)):
    config = load_config()
    config['satellites'] = [s for s in config['satellites'] if s['norad_id'] != norad_id]
    save_config(config)
    return {"status": "success"}

@app.post("/update-location")
async def update_location(name: str = Form(...), lat: float = Form(...), lon: float = Form(...), ele: float = Form(...)):
    config = load_config()
    config['ground_station'] = {"name": name, "latitude": lat, "longitude": lon, "elevation_m": ele}
    save_config(config)
    return {"status": "success"}

@app.post("/refresh-maps")
async def refresh_maps():
    success_2d = generate_2d_map("static/satellite_track_2d.html")
    success_3d = generate_3d_map("static/satellite_track_3d.html")
    success_sky = generate_sky_view("static/satellite_sky_view.html")
    return {"status": "success" if (success_2d and success_3d and success_sky) else "failed"}

if __name__ == "__main__":
    import uvicorn
    fetch_active_catalog() # Uygulama açılırken kataloğu hazırla
    uvicorn.run(app, host="0.0.0.0", port=8000)
