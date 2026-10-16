"""
Descarga focos de calor históricos de NASA FIRMS (Fire Information for Resource
Management System) para una región (bbox) y rango de fechas, y los guarda como CSV.

Uso:
    python fetch_firms.py --bbox -79.4517 -7.7592 -77.7389 -4.5519 --days 10 --out data/firms_raw.csv

Requiere FIRMS_MAP_KEY en tu .env (gratis en https://firms.modaps.eosdis.nasa.gov/api/)
"""
import argparse
import os
import sys
import time
from datetime import date, timedelta
from io import StringIO
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

FIRMS_AREA_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
DEFAULT_SENSOR = "VIIRS_SNPP_NRT"


def _fetch_chunk(api_key: str, bbox_str: str, sensor: str, days: int,
                 start_date: str = None) -> pd.DataFrame | None:
    """Descarga un bloque de hasta 5 días (límite de NASA FIRMS)."""
    url = f"{FIRMS_AREA_URL}/{api_key}/{sensor}/{bbox_str}/{days}"
    if start_date:
        url += f"/{start_date}"

    response = requests.get(url, timeout=60)
    if response.status_code == 200 and "Invalid" not in response.text[:60]:
        df_chunk = pd.read_csv(StringIO(response.text))
        if not df_chunk.empty and "latitude" in df_chunk.columns:
            return df_chunk
    print(f"⚠️ Aviso en chunk de FIRMS ({start_date or 'últimos'}): {response.text[:200]}")
    return None


def fetch_firms_area(bbox_str: str, days: int, sensor: str = DEFAULT_SENSOR,
                     start_date: str = None) -> pd.DataFrame:
    """
    Descarga focos de calor reales de NASA FIRMS para un bounding box
    (west,south,east,north) y una ventana de `days` días.

    Si `start_date` (YYYY-MM-DD) es None, descarga los últimos `days` días (NRT).
    Si se indica, descarga la ventana histórica [start_date, start_date+days),
    necesaria para construir datasets MULTI-FECHA (panel temporal).
    """
    api_key = os.getenv("FIRMS_MAP_KEY")
    if not api_key:
        raise RuntimeError("Falta FIRMS_MAP_KEY en tu archivo .env")

    dfs = []
    chunk_days = 5  # NASA FIRMS acepta 1-5 días por llamada

    if start_date:
        cursor = date.fromisoformat(start_date)
        remaining = days
        while remaining > 0:
            req_days = min(remaining, chunk_days)
            chunk = _fetch_chunk(api_key, bbox_str, sensor, req_days, cursor.isoformat())
            if chunk is not None:
                dfs.append(chunk)
            cursor += timedelta(days=req_days)
            remaining -= req_days
            if remaining > 0:
                time.sleep(0.5)
    else:
        remaining = days
        while remaining > 0:
            req_days = min(remaining, chunk_days)
            chunk = _fetch_chunk(api_key, bbox_str, sensor, req_days)
            if chunk is not None:
                dfs.append(chunk)
            remaining -= chunk_days
            if remaining > 0:
                time.sleep(0.5)

    if dfs:
        return pd.concat(dfs, ignore_index=True).drop_duplicates(
            subset=["latitude", "longitude", "acq_date", "acq_time"]
        )
    return pd.DataFrame()


def main():
    parser = argparse.ArgumentParser(description="Descarga focos de calor de NASA FIRMS por área georeferenciada")
    parser.add_argument("--bbox", nargs=4, type=float, default=[-79.4517, -7.7592, -77.7389, -4.5519],
                        help="West South East North (ej: -79.4517 -7.7592 -77.7389 -4.5519 para Cajamarca)")
    parser.add_argument("--days", type=int, default=10, help="Días hacia atrás (máx 366)")
    parser.add_argument("--start-date", default=None,
                        help="Fecha de inicio (YYYY-MM-DD) para una ventana histórica (multi-fecha)")
    parser.add_argument("--sensor", default=DEFAULT_SENSOR)
    parser.add_argument("--out", default="data/firms_raw.csv")
    args = parser.parse_args()

    west, south, east, north = args.bbox
    bbox_str = f"{west},{south},{east},{north}"

    print(f"📡 Descargando focos de calor de NASA FIRMS para bbox [{bbox_str}]...")
    df = fetch_firms_area(bbox_str, args.days, args.sensor, start_date=args.start_date)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"✅ {len(df)} focos de calor reales guardados en {out_path}")


if __name__ == "__main__":
    main()

