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


def fetch_firms_area(bbox_str: str, days: int, sensor: str = DEFAULT_SENSOR) -> pd.DataFrame:
    """
    Descarga focos de calor de los últimos `days` días para un bounding box (west,south,east,north).
    Realiza solicitudes en bloques de máximo 5 días (límite de NASA FIRMS).
    """
    api_key = os.getenv("FIRMS_MAP_KEY")
    if not api_key:
        raise RuntimeError("Falta FIRMS_MAP_KEY en tu archivo .env")

    dfs = []
    # NASA FIRMS API de área acepta días entre 1 y 5 por llamada
    chunk_days = 5
    remaining = days
    
    while remaining > 0:
        req_days = min(remaining, chunk_days)
        url = f"{FIRMS_AREA_URL}/{api_key}/{sensor}/{bbox_str}/{req_days}"
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200 and "Invalid" not in response.text:
            df_chunk = pd.read_csv(StringIO(response.text))
            if not df_chunk.empty and "latitude" in df_chunk.columns:
                dfs.append(df_chunk)
        else:
            print(f"⚠️ Aviso en chunk de FIRMS: {response.text[:200]}")
            
        remaining -= chunk_days
        if remaining > 0:
            time.sleep(0.5)

    if dfs:
        full_df = pd.concat(dfs, ignore_index=True).drop_duplicates(subset=["latitude", "longitude", "acq_date", "acq_time"])
        return full_df
    return pd.DataFrame()


def main():
    parser = argparse.ArgumentParser(description="Descarga focos de calor de NASA FIRMS por área georeferenciada")
    parser.add_argument("--bbox", nargs=4, type=float, default=[-79.4517, -7.7592, -77.7389, -4.5519],
                        help="West South East North (ej: -79.4517 -7.7592 -77.7389 -4.5519 para Cajamarca)")
    parser.add_argument("--days", type=int, default=10, help="Días hacia atrás (máx 366)")
    parser.add_argument("--sensor", default=DEFAULT_SENSOR)
    parser.add_argument("--out", default="data/firms_raw.csv")
    args = parser.parse_args()

    west, south, east, north = args.bbox
    bbox_str = f"{west},{south},{east},{north}"

    print(f"📡 Descargando focos de calor de NASA FIRMS para bbox [{bbox_str}]...")
    df = fetch_firms_area(bbox_str, args.days, args.sensor)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"✅ {len(df)} focos de calor reales guardados en {out_path}")


if __name__ == "__main__":
    main()

