# -*- coding: utf-8 -*-
"""
Construye un PANEL MULTI-FECHA REAL (temporadas secas 2024, 2025 y 2026) para
Cajamarca reutilizando las capas estáticas reales ya validadas (DEM Copernicus,
OSM y mosaico Sentinel-2 NDVI con 99.48% de cobertura) e incorporando, para cada
fecha de referencia:
  - Focos de calor históricos reales de NASA FIRMS (VIIRS_SNPP_SP / VIIRS_SNPP_NRT)
  - Meteorología ERA5 real (Open-Meteo Archive) con lags, lluvia acumulada y sequía
  - Features espaciales (vecindario KNN geográfico) y físicas (VPD, viento×pendiente, FWI)

Salida:
  - data/dataset_panel.parquet (panel multi-fecha para entrenamiento y validación espacio-temporal)
  - data/firms_multidate.csv   (archivo consolidado de focos reales descargados)

Uso:
    python data_pipeline/build_multidate_panel.py
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.model import compute_physical_features  # noqa: E402
from data_pipeline.fetch_firms import fetch_firms_area  # noqa: E402
from data_pipeline.real_features import fetch_meteo  # noqa: E402

load_dotenv(ROOT / ".env")

CAJAMARCA_BBOX = (-7.7592, -79.4517, -4.5519, -77.7389)  # min_lat, min_lon, max_lat, max_lon
FIRMS_BBOX_STR = "-79.4517,-7.7592,-77.7389,-4.5519"     # west,south,east,north

# 12 fechas de referencia cubriendo 3 temporadas secas reales en Cajamarca:
#   - 2024 y 2025 (VIIRS_SNPP_SP archivo estándar) -> entrenamiento / CV espacial
#   - 2026        (VIIRS_SNPP_NRT)                 -> validación temporal futura
DEFAULT_SCHEDULE = [
    ("2024-07-25", "VIIRS_SNPP_SP"),
    ("2024-08-15", "VIIRS_SNPP_SP"),
    ("2024-09-05", "VIIRS_SNPP_SP"),
    ("2024-09-25", "VIIRS_SNPP_SP"),
    ("2024-10-15", "VIIRS_SNPP_SP"),
    ("2024-11-05", "VIIRS_SNPP_SP"),
    ("2025-08-01", "VIIRS_SNPP_SP"),
    ("2025-08-25", "VIIRS_SNPP_SP"),
    ("2025-09-15", "VIIRS_SNPP_SP"),
    ("2025-10-10", "VIIRS_SNPP_SP"),
    ("2026-08-20", "VIIRS_SNPP_NRT"),
    ("2026-09-06", "VIIRS_SNPP_NRT"),
]

CELL_SIZE = 0.009
STATIC_COLS = [
    "grid_id", "longitude", "latitude", "spatial_block_id",
    "elevacion_m", "pendiente_pct", "orientacion",
    "dist_carretera_m", "dist_poblado_m", "ndvi", "ndvi_anomaly",
]


def _interp_meteo_to_grid(base_coords: np.ndarray, meteo_df: pd.DataFrame) -> dict[str, np.ndarray]:
    """Interpolación ponderada por inversa de distancia (IDW, k=4) de ERA5 a cada celda."""
    m_coords = np.column_stack([meteo_df["longitude"].to_numpy(float), meteo_df["latitude"].to_numpy(float)])
    tree = cKDTree(m_coords)
    k = min(4, len(m_coords))
    dists, idxs = tree.query(base_coords, k=k)
    if k == 1:
        dists, idxs = dists[:, None], idxs[:, None]
    w = 1.0 / np.maximum(dists, 1e-4)
    w /= w.sum(axis=1, keepdims=True)

    out = {}
    scalar_cols = [
        "temp_2m", "humedad_relativa", "viento_velocidad",
        "dias_sin_lluvia", "lluvia_acum_7d", "lluvia_acum_15d",
        "temp_lag1", "humedad_lag1",
    ]
    for col in scalar_cols:
        vals = meteo_df[col].to_numpy(float)[idxs]
        out[col] = np.round(np.sum(vals * w, axis=1), 2)

    # Dirección del viento por promedio vectorial (sin/cos)
    ang = np.deg2rad(meteo_df["viento_direccion"].to_numpy(float)[idxs])
    s_mean = np.sum(np.sin(ang) * w, axis=1)
    c_mean = np.sum(np.cos(ang) * w, axis=1)
    norm = np.maximum(np.hypot(s_mean, c_mean), 1e-6)
    out["viento_dir_sin"] = np.round(s_mean / norm, 4)
    out["viento_dir_cos"] = np.round(c_mean / norm, 4)
    out["viento_direccion"] = np.round(np.rad2deg(np.arctan2(s_mean, c_mean)) % 360.0, 1)
    return out


def _assign_fires_fast(firms_df: pd.DataFrame, base_df: pd.DataFrame) -> np.ndarray:
    """Asigna focos FIRMS a la celda más cercana (tolerancia <= media diagonal de celda)."""
    counts = np.zeros(len(base_df), dtype=np.int32)
    if firms_df.empty or "latitude" not in firms_df.columns:
        return counts

    # Filtrar focos de baja confianza ('l') para evitar falsos positivos industriales
    clean = firms_df.copy()
    if "confidence" in clean.columns:
        conf_str = clean["confidence"].astype(str).str.lower().str.strip()
        clean = clean[conf_str != "l"]
    if clean.empty:
        return counts

    grid_coords = np.column_stack([base_df["longitude"].to_numpy(float), base_df["latitude"].to_numpy(float)])
    fire_coords = np.column_stack([clean["longitude"].to_numpy(float), clean["latitude"].to_numpy(float)])
    tree = cKDTree(grid_coords)
    dists, idxs = tree.query(fire_coords, k=1)
    max_dist = CELL_SIZE * 0.75
    valid = dists <= max_dist
    for idx in idxs[valid]:
        counts[int(idx)] += 1
    return counts


def build_panel(
    base_dataset_path: str = "data/dataset.parquet",
    out_panel_path: str = "data/dataset_panel.parquet",
    out_firms_path: str = "data/firms_multidate.csv",
) -> pd.DataFrame:
    base_path = Path(base_dataset_path)
    base_df = pd.read_parquet(base_path)[STATIC_COLS].copy()
    print(f"📦 Base estática cargada: {len(base_df):,} celdas desde {base_path}")

    # Precomputar vecinos KNN geográficos (k=8, excluyendo propia celda) UNA sola vez
    lats = base_df["latitude"].to_numpy(float)
    lons = base_df["longitude"].to_numpy(float)
    lat0 = np.deg2rad(float(lats.mean()))
    geo_km = np.column_stack([lons * 111.32 * np.cos(lat0), lats * 110.57])
    knn_idx = cKDTree(geo_km).query(geo_km, k=9)[1][:, 1:]
    base_lonlat = np.column_stack([lons, lats])

    all_firms = []
    frames = []
    firms_cache = ROOT / "data" / "cache"
    firms_cache.mkdir(parents=True, exist_ok=True)

    for ref_date, sensor in DEFAULT_SCHEDULE:
        ref_d = date.fromisoformat(ref_date)
        win_start = (ref_d - timedelta(days=9)).isoformat()
        print(f"\n📅 [{ref_date}] ({sensor}) ventana FIRMS {win_start}..{ref_date}")

        # 1) Descargar o leer caché de focos FIRMS para esta ventana de 10 días
        f_cache = firms_cache / f"firms_{sensor}_{ref_date}.csv"
        if f_cache.exists():
            firms_win = pd.read_csv(f_cache)
        else:
            firms_win = fetch_firms_area(FIRMS_BBOX_STR, days=10, sensor=sensor, start_date=win_start)
            firms_win.to_csv(f_cache, index=False)
            time.sleep(0.4)

        if not firms_win.empty:
            firms_win["ref_date"] = ref_date
            all_firms.append(firms_win)

        # 2) Descargar o leer caché de meteorología ERA5 real para esta fecha
        meteo_df = fetch_meteo(CAJAMARCA_BBOX, ref_date, ventana_dias=20, step=0.25)
        meteo_interp = _interp_meteo_to_grid(base_lonlat, meteo_df)

        # 3) Ensamblar frame de la fecha
        frame = base_df.copy()
        for col, arr in meteo_interp.items():
            frame[col] = arr

        # Vecindario geográfico KNN (sin fuga al bloque de CV)
        frame["temp_vecindad_media"] = np.round(frame["temp_2m"].to_numpy(float)[knn_idx].mean(axis=1), 1)
        frame["humedad_vecindad_media"] = np.round(frame["humedad_relativa"].to_numpy(float)[knn_idx].mean(axis=1), 1)

        # Variables físicas compuestas (VPD, viento×pendiente, índice de sequedad)
        vpd, vp, seq = compute_physical_features(
            frame["temp_2m"].to_numpy(float),
            frame["humedad_relativa"].to_numpy(float),
            frame["viento_velocidad"].to_numpy(float),
            frame["pendiente_pct"].to_numpy(float),
            frame["dias_sin_lluvia"].to_numpy(float),
        )
        frame["vpd_kpa"] = vpd
        frame["viento_pendiente"] = vp
        frame["indice_sequedad"] = seq

        # Estacionalidad (ahora SÍ varía entre meses julio–noviembre)
        mes = ref_d.month
        frame["mes_sin"] = round(float(np.sin(2 * np.pi * mes / 12.0)), 4)
        frame["mes_cos"] = round(float(np.cos(2 * np.pi * mes / 12.0)), 4)

        # Etiqueta observacional pura (focos FIRMS nominal/high)
        fire_counts = _assign_fires_fast(firms_win, base_df)
        frame["fire_count"] = fire_counts
        frame["target"] = (fire_counts > 0).astype(np.int8)
        frame["ref_date"] = ref_date
        frame["year"] = ref_d.year

        n_pos = int(frame["target"].sum())
        print(f"   -> Focos brutos: {len(firms_win)} | Celdas positivas (target=1): {n_pos}")
        frames.append(frame)

    panel = pd.concat(frames, ignore_index=True)
    out_p = Path(out_panel_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(out_p, index=False)

    if all_firms:
        firms_all = pd.concat(all_firms, ignore_index=True)
        Path(out_firms_path).parent.mkdir(parents=True, exist_ok=True)
        firms_all.to_csv(out_firms_path, index=False)

    print("\n" + "═" * 74)
    print(f"✅ PANEL MULTI-FECHA GENERADO: {out_p}")
    print(f"   • Fechas de referencia : {len(DEFAULT_SCHEDULE)} (2024, 2025 y 2026)")
    print(f"   • Filas totales        : {len(panel):,}")
    print(f"   • Positivos (target=1) : {int(panel['target'].sum()):,} ({panel['target'].mean():.3%})")
    print("   • Por año:")
    for yr, grp in panel.groupby("year"):
        print(f"       - {yr}: {len(grp):,} filas | {int(grp['target'].sum()):,} positivos ({grp['target'].mean():.3%})")
    print("═" * 74)
    return panel


def main():
    parser = argparse.ArgumentParser(description="Construye panel multi-fecha real (2024–2026) para Cajamarca")
    parser.add_argument("--base", default="data/dataset.parquet")
    parser.add_argument("--out", default="data/dataset_panel.parquet")
    parser.add_argument("--firms-out", default="data/firms_multidate.csv")
    args = parser.parse_args()
    build_panel(args.base, args.out, args.firms_out)


if __name__ == "__main__":
    main()

