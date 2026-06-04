import json
import os
import requests
from skyfield.api import load, EarthSatellite, wgs84
from datetime import datetime, timezone, timedelta

CONFIG_FILE = "config.json"
TLE_DATA_DIR = "tle_cache"

if not os.path.exists(TLE_DATA_DIR):
    os.makedirs(TLE_DATA_DIR)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"satellites": [], "ground_station": {"name": "Default", "latitude": 0, "longitude": 0, "elevation_m": 0}}
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def fetch_active_catalog():
    """Celestrak'tan tüm aktif uyduların listesini indirir ve cache'ler."""
    cache_path = os.path.join(TLE_DATA_DIR, "active_catalog.txt")
    
    # Günde sadece 1 kez indir
    if os.path.exists(cache_path):
        file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_path))
        if file_age < timedelta(hours=24):
            with open(cache_path, 'r') as f:
                return f.read().splitlines()

    print("📡 Aktif uydu kataloğu indiriliyor (Celestrak)...")
    # Güncel Celestrak GP API URL'si
    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        with open(cache_path, 'w') as f:
            f.write(response.text)
        return response.text.splitlines()
    except Exception as e:
        print(f"❌ Katalog indirilemedi: {e}")
        return []

def fetch_tle_by_norad_id(norad_id, force_refresh=False):
    """Belirli bir NORAD ID için Celestrak'tan doğrudan TLE indirir ve cache'ler.

    Aktif katalogda olmayan (ör. yeni fırlatılan) uydular için fallback.
    Per-satellite cache: tle_cache/<norad_id>.tle, 6 saatlik TTL.
    """
    norad_id = str(norad_id).strip()
    if not norad_id.isdigit():
        return None

    cache_path = os.path.join(TLE_DATA_DIR, f"{norad_id}.tle")

    if not force_refresh and os.path.exists(cache_path):
        file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_path))
        if file_age < timedelta(hours=6):
            with open(cache_path, "r") as f:
                lines = [ln.rstrip("\n") for ln in f.readlines() if ln.strip()]
            if len(lines) >= 3:
                return lines[0].strip(), lines[1], lines[2]

    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={norad_id}&FORMAT=tle"
    try:
        # Timeout'u 5 saniyeye düşürüp sistemin kilitlenmesini önleyelim
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        text = resp.text.strip()
        if not text or "No GP data found" in text:
            return None
        lines = [ln.rstrip("\r\n") for ln in text.splitlines() if ln.strip()]
        if len(lines) < 3:
            return None
        with open(cache_path, "w") as f:
            f.write("\n".join(lines[:3]) + "\n")
        return lines[0].strip(), lines[1], lines[2]
    except (requests.exceptions.RequestException, Exception) as e:
        # Hata logunu sessize alıp sistemin akışını bozmayalım
        # print(f"⚠️ TLE indirilemedi (NORAD {norad_id}): {e}")
        return None


def parse_cdm_xml(content):
    """CDM XML içeriğini parse eder ve kritik bilgileri döner."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(content)
        # Namespace handling
        ns = {'ndm': 'urn:ccsds:schema:ndmxml'}
        
        # Basit bir eşleme (CDM formatına göre değişebilir)
        sat1 = root.find(".//OBJECT1/OBJECT_NAME", ns)
        sat2 = root.find(".//OBJECT2/OBJECT_NAME", ns)
        dist = root.find(".//RELATIVE_METADATA/MISS_DISTANCE", ns)
        prob = root.find(".//RELATIVE_METADATA/COLLISION_PROBABILITY", ns)
        
        return {
            "satellite_1": sat1.text if sat1 is not None else "Unknown",
            "satellite_2": sat2.text if sat2 is not None else "Unknown",
            "distance_km": float(dist.text) / 1000.0 if dist is not None else 0.0,
            "probability": prob.text if prob is not None else "N/A",
            "source": "CDM (Precision)"
        }
    except Exception as e:
        print(f"CDM Parse Error: {e}")
        return None

def get_satellite_from_catalog(name_or_id):
    """Katalog içinde isim veya NORAD ID ile arama yapar, TLE döner.

    Önce günlük 'active' kataloğuna bakar; bulamazsa Celestrak CATNR
    endpoint'ine düşer (yeni uydular için).
    """
    catalog = fetch_active_catalog()
    # Katalog 3 satırlı formatta (Name, Line 1, Line 2)
    for i in range(0, len(catalog) - 2, 3):
        name = catalog[i].strip()
        line1 = catalog[i+1]
        line2 = catalog[i+2]
        try:
            norad_id = line2.split()[1]
        except IndexError:
            continue

        if str(name_or_id).upper() in name.upper() or str(name_or_id) == norad_id:
            return name, line1, line2

    # Aktif katalogda yoksa NORAD ID ile direkt indirmeyi dene
    if str(name_or_id).strip().isdigit():
        return fetch_tle_by_norad_id(name_or_id)
    return None

def get_active_satellites():
    """Config'deki uyduları ve seçili analiz uydusunu döner."""
    config = load_config()
    ts = load.timescale()
    sat_objects = []
    
    for sat_info in config.get('satellites', []):
        data = get_satellite_from_catalog(sat_info['norad_id'])
        if data:
            sat_objects.append(EarthSatellite(data[1], data[2], data[0], ts))
    
    return sat_objects, config

def get_ground_station():
    config = load_config()
    gs = config['ground_station']
    return wgs84.latlon(gs['latitude'], gs['longitude'], gs.get('elevation_m', 0)), gs

def get_upcoming_passes(satellite, ground_station, hours=24):
    """Belirli bir uydu için yer istasyonundan görünecek geçişleri hesaplar."""
    ts = load.timescale()
    now = datetime.now(timezone.utc)
    t0 = ts.from_datetime(now)
    t1 = ts.from_datetime(now + timedelta(hours=hours))
    
    # 10 derece üzerindeki geçişleri bul (altitude > 10)
    t, events = satellite.find_events(ground_station, t0, t1, altitude_degrees=10.0)
    
    passes = []
    current_pass = {}
    
    for ti, event in zip(t, events):
        name = ('Rise', 'Culminate', 'Set')[event]
        diff = (satellite - ground_station).at(ti)
        alt, az, dist = diff.altaz()
        
        event_data = {
            "time": ti.utc_strftime('%H:%M:%S'),
            "datetime": ti.utc_datetime(),
            "azimuth": round(az.degrees, 1),
            "elevation": round(alt.degrees, 1),
            "type": name
        }
        
        if event == 0: # AOS (Rise)
            current_pass = {"aos": event_data}
        elif event == 1: # MAX (Peak)
            current_pass["max"] = event_data
        elif event == 2: # LOS (Set)
            if "aos" in current_pass:
                current_pass["los"] = event_data
                current_pass["satellite"] = satellite.name
                # Süre hesapla
                duration = (current_pass['los']['datetime'] - current_pass['aos']['datetime']).total_seconds() / 60
                current_pass["duration_min"] = round(duration, 1)
                passes.append(current_pass)
                current_pass = {}
                
    return passes

def get_satellite_live_state(satellite, ground_station=None):
    """Bir uydunun şu anki canlı durumunu hesaplar.

    Returns dict: latitude, longitude, altitude_km, velocity_km_s,
                  azimuth, elevation, range_km (yer istasyonu verildiyse),
                  timestamp_utc.
    """
    ts = load.timescale()
    now = datetime.now(timezone.utc)
    t = ts.from_datetime(now)

    geocentric = satellite.at(t)
    subpoint = wgs84.subpoint(geocentric)

    # Hız büyüklüğü (km/s) — geocentric.velocity.km_per_s vector
    try:
        vx, vy, vz = geocentric.velocity.km_per_s
        velocity_km_s = round((vx * vx + vy * vy + vz * vz) ** 0.5, 3)
    except Exception:
        velocity_km_s = None

    state = {
        "latitude": round(subpoint.latitude.degrees, 4),
        "longitude": round(subpoint.longitude.degrees, 4),
        "altitude_km": round(subpoint.elevation.km, 2),
        "velocity_km_s": velocity_km_s,
        "timestamp_utc": now.isoformat(),
    }

    if ground_station is not None:
        try:
            diff = (satellite - ground_station).at(t)
            alt, az, dist = diff.altaz()
            state["azimuth"] = round(az.degrees, 2)
            state["elevation"] = round(alt.degrees, 2)
            state["range_km"] = round(dist.km, 2)
            state["above_horizon"] = bool(alt.degrees > 0)
        except Exception:
            pass

    return state


def get_next_pass_summary(satellite, ground_station, hours=24):
    """En yakın gelecek geçişi (varsa) özet dict olarak döner."""
    passes = get_upcoming_passes(satellite, ground_station, hours=hours)
    now = datetime.now(timezone.utc)
    upcoming = [p for p in passes if p["aos"]["datetime"] > now]
    if not upcoming:
        return None
    next_p = upcoming[0]
    minutes_until = (next_p["aos"]["datetime"] - now).total_seconds() / 60.0
    return {
        "satellite": next_p["satellite"],
        "aos_time": next_p["aos"]["time"],
        "aos_datetime": next_p["aos"]["datetime"].isoformat(),
        "max_elevation": next_p["max"]["elevation"],
        "duration_min": next_p["duration_min"],
        "minutes_until": round(minutes_until, 1),
    }


def send_telegram_alert(message):
    """Telegram üzerinden bildirim gönderir."""
    config = load_config()
    bot_token = config.get("telegram", {}).get("bot_token")
    chat_id = config.get("telegram", {}).get("chat_id")
    
    if not bot_token or not chat_id:
        # print("⚠️ Telegram ayarları yapılmamış.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Telegram gönderilemedi: {e}")
        return False

if __name__ == "__main__":
    # Test
    ts = load.timescale()
    sats, cfg = get_active_satellites()
    gs, _ = get_ground_station()
    if sats:
        print(f"📡 {sats[0].name} için geçişler hesaplanıyor...")
        p = get_upcoming_passes(sats[0], gs)
        print(f"✅ {len(p)} geçiş bulundu.")
    
    # Telegram Test
    # send_telegram_alert("🚀 Satellite Tracking System Online!")

if __name__ == "__main__":
    # Test etmek için basit bir kontrol
    try:
        sats, cfg = get_active_satellites()
        print(f"\n🚀 Test: {len(sats)} uydu başarıyla çekildi.")
    except Exception as e:
        print(f"🔴 Test hatası: {e}")
