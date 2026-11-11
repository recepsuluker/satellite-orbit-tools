from datetime import datetime, timezone

import pandas as pd
from skyfield.api import load

from satorbit.mission_control.utils import get_active_satellites, get_ground_station


def main():
    try:
        # Konfigürasyonu ve uyduları yükle
        satellites, config = get_active_satellites()
        station, station_info = get_ground_station()

        if not satellites:
            print("❌ İşlenecek uydu bulunamadı.")
            return

        print(
            f"📡 Analiz Konumu: {station_info['name']} ({station_info['latitude']}, {station_info['longitude']})"
        )

        ts = load.timescale()
        now = datetime.now(timezone.utc)

        # Önümüzdeki 24 saati (saatlik) hesaplayalım
        times = ts.utc(now.year, now.month, now.day, range(now.hour, now.hour + 24))

        all_data = []
        for satellite in satellites:
            print(f"🛰️ {satellite.name} için yer istasyonu analizi yapılıyor...")
            for t in times:
                # Uydu ile yer istasyonu arasındaki görece konum
                difference = satellite - station
                topocentric = difference.at(t)
                alt, az, distance = topocentric.altaz()

                # Subpoint (Dünya üzerindeki izdüşümü)
                geocentric = satellite.at(t)
                subpoint = load("wgs84").subpoint(geocentric)

                all_data.append(
                    {
                        "satellite": satellite.name,
                        "utc_time": t.utc_strftime("%Y-%m-%d %H:%M:%S"),
                        "azimuth_deg": az.degrees,
                        "elevation_deg": alt.degrees,
                        "range_km": distance.km,
                        "lat": subpoint.latitude.degrees,
                        "lon": subpoint.longitude.degrees,
                        "is_visible": alt.degrees > 0,  # Ufkun üzerinde mi?
                    }
                )

        df = pd.DataFrame(all_data)
        df.to_csv("satellite_analysis.csv", index=False)

        visible_count = df[df["is_visible"]].shape[0]
        print("\n✅ Analiz Tamamlandı!")
        print(f"📊 Toplam Veri: {len(df)} | Ufkun Üzerindeki (Görünür) Noktalar: {visible_count}")
        print("📂 Sonuçlar 'satellite_analysis.csv' dosyasına kaydedildi.")

    except Exception as e:
        print(f"🔴 Bir hata oluştu: {e}")


if __name__ == "__main__":
    main()
