"""
Convierte puntos de calor (lat/lon) de NASA FIRMS en un dataset estructurado
de grillas de 1km², con la columna Target (1 = incendio, 0 = no incendio) y
características REALES de terreno, vegetación, meteorología e infraestructura.

Fuentes de datos REALES (todas abiertas, sin credenciales):
  - NASA FIRMS              -> focos de calor (etiqueta observacional)
  - Copernicus DEM GLO-30   -> pendiente, aspecto y elevación
  - Sentinel-2 L2A (AWS)    -> NDVI real
  - ERA5 vía Open-Meteo     -> temperatura, humedad, viento, lluvia, sequía
  - OpenStreetMap (Overpass)-> distancias reales a vías y poblados

Este es el script central de las Semanas 3-5.

Uso:
    python grid_builder.py --firms data/firms_raw.csv --ref-date 2026-09-06 \\
        --start 2026-08-15 --end 2026-09-06 --out data/dataset.parquet

    # Modo sin red (features sintéticas de respaldo, NO recomendado para métricas):
    python grid_builder.py --synthetic

Coordenadas extremas (Puntos de lectura de Cajamarca):
    Norte: 04° 33′ 07″ S, 78° 42′ 27″ O (Cordillera Campanquiz / Ecuador) -> Lat: -4.5519, Lon: -78.7075
    Sur:   07° 45′ 33″ S, 78° 13′ 14″ O (Límite La Libertad)             -> Lat: -7.7592, Lon: -78.2206
    Este:  07° 27′ 47″ S, 77° 44′ 20″ O (Río Marañón)                    -> Lat: -7.4631, Lon: -77.7389
    Oeste: 06° 23′ 41″ S, 79° 27′ 06″ O (Cerro Carrampón)                -> Lat: -6.3947, Lon: -79.4517
"""
import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from data_pipeline.real_features import attach_real_features

CELL_SIZE_DEG = 0.009  # ~1km en el ecuador (0.009 grados aprox)

# Valores de respaldo si una fuente real no cubre una celda
DEFAULTS = {
    "pendiente_pct": 8.0, "ndvi": 0.40, "dist_carretera_m": 3000.0, "dist_poblado_m": 5000.0,
    "temp_2m": 20.0, "humedad_relativa": 55.0, "viento_velocidad": 10.0, "viento_direccion": 180.0,
    "dias_sin_lluvia": 10.0, "lluvia_acum_7d": 5.0, "lluvia_acum_15d": 15.0,
    "temp_lag1": 20.0, "humedad_lag1": 55.0,
}


def build_grid(min_lat: float, min_lon: float, max_lat: float, max_lon: float,
               cell_size: float = CELL_SIZE_DEG) -> gpd.GeoDataFrame:
    """Genera una grilla regular de celdas de ~1km² cubriendo el bounding box dado."""
    lons = np.arange(min_lon, max_lon, cell_size)
    lats = np.arange(min_lat, max_lat, cell_size)

    cells = []
    for lon in lons:
        for lat in lats:
            cells.append({
                "grid_id": f"{lon:.4f}_{lat:.4f}",
                "longitude": lon + cell_size / 2.0,
                "latitude": lat + cell_size / 2.0,
                "geometry": box(lon, lat, lon + cell_size, lat + cell_size),
            })

    return gpd.GeoDataFrame(cells, crs="EPSG:4326")


def assign_fires_to_grid(firms_df: pd.DataFrame, grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Marca con Target=1 las celdas de la grilla que contienen un foco de calor satelital real (FIRMS).
    La etiqueta es puramente observacional (sin fuga de información / data leakage).
    """
    grid["fire_count"] = 0
    if not firms_df.empty and "longitude" in firms_df.columns:
        fires_gdf = gpd.GeoDataFrame(
            firms_df,
            geometry=gpd.points_from_xy(firms_df["longitude"], firms_df["latitude"]),
            crs="EPSG:4326",
        )
        joined = gpd.sjoin(fires_gdf, grid, how="inner", predicate="within")
        fire_counts = joined.groupby("grid_id").size().to_dict()
        grid["fire_count"] = grid["grid_id"].map(fire_counts).fillna(0).astype(int)

    grid["target"] = (grid["fire_count"] > 0).astype(int)
    return grid


def add_spatial_blocks(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Bloques espaciales de ~50km x 50km para la validación cruzada espacial."""
    lats = grid["latitude"].values
    lons = grid["longitude"].values
    block_lat = ((lats - lats.min()) // 0.45).astype(int)
    block_lon = ((lons - lons.min()) // 0.45).astype(int)
    grid["spatial_block_id"] = [f"block_{a}_{b}" for a, b in zip(block_lat, block_lon)]
    return grid


def _generate_synthetic_features(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Respaldo SIN RED: genera features sintéticas (solo para pruebas, no para métricas)."""
    np.random.seed(42)
    n = len(grid)
    lats = grid["latitude"].values
    lons = grid["longitude"].values

    elevation_sim = 1500 + (lats - lats.min()) * 400 + np.sin(lons * 50) * 600
    slope = np.abs(np.gradient(elevation_sim)) * 15 + np.random.uniform(2, 25, size=n)
    grid["pendiente_pct"] = np.round(np.clip(slope, 1.0, 45.0), 2)

    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    aspect_angles = (np.arctan2(np.sin(lats), np.cos(lons)) * 180 / np.pi + 180) % 360
    grid["viento_direccion"] = np.round((aspect_angles + np.random.normal(0, 15, n)) % 360, 1)
    grid["orientacion"] = [dirs[int(deg // 45) % 8] for deg in aspect_angles]

    ndvi_base = 0.45 + 0.2 * np.sin(lats * 20) + np.random.normal(0, 0.08, n)
    grid["ndvi"] = np.round(np.clip(ndvi_base, 0.05, 0.85), 3)

    road_hubs = [(-78.51, -7.16), (-78.80, -6.50), (-79.10, -5.80)]
    town_hubs = [(-78.50, -7.15), (-78.75, -6.70), (-79.00, -6.00)]
    min_dist_road = np.zeros(n)
    min_dist_town = np.zeros(n)
    for i in range(n):
        clon, clat = lons[i], lats[i]
        min_dist_road[i] = min(np.sqrt((clon - rx) ** 2 + (clat - ry) ** 2) * 111000 for rx, ry in road_hubs)
        min_dist_town[i] = min(np.sqrt((clon - tx) ** 2 + (clat - ty) ** 2) * 111000 for tx, ty in town_hubs)
    grid["dist_carretera_m"] = np.round(min_dist_road + np.random.uniform(50, 500, n), 1)
    grid["dist_poblado_m"] = np.round(min_dist_town + np.random.uniform(100, 1000, n), 1)

    grid["temp_2m"] = np.round(22.0 + (lats - lats.mean()) * -1.5 + np.random.normal(0, 3.5, n), 1)
    grid["humedad_relativa"] = np.round(np.clip(45.0 - (grid["temp_2m"] - 20) * 1.5 + np.random.normal(0, 8, n), 15.0, 95.0), 1)
    grid["viento_velocidad"] = np.round(np.clip(12.0 + (grid["pendiente_pct"] / 3.0) + np.random.normal(0, 4, n), 3.0, 55.0), 1)

    dias_sin_lluvia = np.clip(20.0 - (grid["humedad_relativa"] / 4.5) + np.random.normal(0, 2.5, n), 0, 50).round(1)
    grid["dias_sin_lluvia"] = dias_sin_lluvia
    grid["lluvia_acum_7d"] = np.round(np.clip(45.0 - dias_sin_lluvia * 2.2 + np.random.normal(0, 5, n), 0.0, 160.0), 1)
    grid["lluvia_acum_15d"] = np.round(np.clip(95.0 - dias_sin_lluvia * 3.8 + np.random.normal(0, 10, n), 0.0, 320.0), 1)
    grid["temp_lag1"] = np.round(grid["temp_2m"] + np.random.normal(0, 1.2, n), 1)
    grid["humedad_lag1"] = np.round(np.clip(grid["humedad_relativa"] + np.random.normal(0, 3.0, n), 10.0, 98.0), 1)
    return grid


def compute_geospatial_features(grid: gpd.GeoDataFrame, bbox: tuple, ref_date: str,
                                start: str, end: str, use_real: bool = True) -> gpd.GeoDataFrame:
    """
    Calcula todas las variables del dataset:
      (a) Features base (reales o sintéticas de respaldo)
      (b) Features derivadas (anomalía NDVI, medias de vecindario, estacionalidad)
      (c) Baseline físico (risk_score_baseline) y etiqueta honesta (target)
    """
    grid = add_spatial_blocks(grid)

    # ── (a) Features base ────────────────────────────────────────────────────
    if use_real:
        print("  🌎 [Datos reales] DEM Copernicus + Sentinel-2 NDVI + ERA5 Open-Meteo + OSM...")
        grid = attach_real_features(grid, bbox, ref_date, start, end)
        for col, val in DEFAULTS.items():
            if col not in grid.columns:
                grid[col] = val
            else:
                grid[col] = pd.to_numeric(grid[col], errors="coerce").fillna(val)
    else:
        print("  ⚠️ [Modo sintético] Generando features de respaldo (sin red)...")
        grid = _generate_synthetic_features(grid)

    # ── (b) Features derivadas ───────────────────────────────────────────────
    ndvi_zona_mean = grid.groupby("spatial_block_id")["ndvi"].transform("mean")
    grid["ndvi_anomaly"] = np.round(grid["ndvi"] - ndvi_zona_mean, 3)
    grid["temp_vecindad_media"] = np.round(grid.groupby("spatial_block_id")["temp_2m"].transform("mean"), 1)
    grid["humedad_vecindad_media"] = np.round(grid.groupby("spatial_block_id")["humedad_relativa"].transform("mean"), 1)

    mes = pd.Timestamp(ref_date).month
    grid["mes_sin"] = np.round(np.sin(2 * np.pi * mes / 12.0), 4)
    grid["mes_cos"] = np.round(np.cos(2 * np.pi * mes / 12.0), 4)

    # ── (c) Baseline físico + etiqueta honesta ───────────────────────────────
    risk_score = (
        (grid["temp_2m"] - 20) * 0.04 -
        (grid["humedad_relativa"] - 50) * 0.03 +
        (grid["viento_velocidad"]) * 0.02 +
        (grid["pendiente_pct"]) * 0.02 +
        (grid["dias_sin_lluvia"]) * 0.025 -
        (grid["lluvia_acum_7d"]) * 0.015 -
        np.log1p(grid["dist_carretera_m"]) * 0.04
    )
    grid["risk_score_baseline"] = np.round(risk_score, 4)

    # Etiqueta honesta: SOLO incendios reales detectados por NASA FIRMS (fire_count > 0).
    grid["target"] = (grid["fire_count"] > 0).astype(int)

    return grid


def main():
    parser = argparse.ArgumentParser(description="Construye dataset de grillas 1km² con Target y Features REALES")
    parser.add_argument("--firms", default="data/firms_raw.csv", help="CSV de fetch_firms.py")
    parser.add_argument("--bbox", nargs=4, type=float, metavar=("MIN_LAT", "MIN_LON", "MAX_LAT", "MAX_LON"),
                        default=[-7.7592, -79.4517, -4.5519, -77.7389],
                        help="Coordenadas extremas de Cajamarca [minLat, minLon, maxLat, maxLon]")
    parser.add_argument("--ref-date", default="2026-09-06", help="Fecha de referencia (fin de la ventana de focos)")
    parser.add_argument("--start", default="2026-08-15", help="Inicio de la ventana meteorológica/NDVI")
    parser.add_argument("--end", default="2026-09-06", help="Fin de la ventana meteorológica/NDVI")
    parser.add_argument("--synthetic", action="store_true", help="Usar features sintéticas (sin red, solo pruebas)")
    parser.add_argument("--out", default="data/dataset.parquet")
    args = parser.parse_args()

    min_lat, min_lon, max_lat, max_lon = args.bbox
    bbox = (min_lat, min_lon, max_lat, max_lon)

    firms_path = Path(args.firms)
    if firms_path.exists():
        firms_df = pd.read_csv(firms_path)
    else:
        print(f"⚠️ Archivo {firms_path} no encontrado, usando datos vacíos.")
        firms_df = pd.DataFrame()

    print("🧩 Construyendo grilla espacial de 1km²...")
    grid = build_grid(min_lat, min_lon, max_lat, max_lon)
    print(f"  -> {len(grid)} celdas de 1km² generadas")

    print("🔥 Asignando focos de calor satelitales (FIRMS)...")
    grid = assign_fires_to_grid(firms_df, grid)
    print(f"  -> {grid['target'].sum()} celdas con Target=1 (incendio detectado)")

    grid = compute_geospatial_features(grid, bbox, args.ref_date, args.start, args.end,
                                       use_real=not args.synthetic)

    # Ordenar dataset: primero celdas con target=1, luego por distancia al centro de Cajamarca (-7.16, -78.50)
    c_lat, c_lon = -7.16, -78.50
    dist = np.sqrt((grid["latitude"] - c_lat) ** 2 + (grid["longitude"] - c_lon) ** 2)
    grid["dist_center"] = dist

    grid = grid.sort_values(by=["target", "dist_center"], ascending=[False, True]).reset_index(drop=True)
    grid = grid.drop(columns=["dist_center"])

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    grid.to_parquet(out_path)
    csv_path = out_path.with_suffix(".csv")
    grid_drop_geom = grid.drop(columns=["geometry"])
    grid_drop_geom.to_csv(csv_path, index=False)

    print(f"✅ Dataset guardado exitosamente en:")
    print(f"   - Parquet: {out_path}")
    print(f"   - CSV: {csv_path}")


if __name__ == "__main__":
    main()
