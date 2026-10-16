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
    "temp_lag1": 20.0, "humedad_lag1": 55.0, "elevacion_m": 2500.0,
}

# Número de vecinos geográficos (~8 celdas de 1 km²) para las features de vecindario.
NEIGHBORHOOD_K = 8


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
    grid["elevacion_m"] = np.round(elevation_sim, 1)
    return grid


def _geo_km(grid: gpd.GeoDataFrame) -> np.ndarray:
    """Coordenadas aproximadas en km (equirectangular centrada en el bbox) para el KNN."""
    lats = grid["latitude"].to_numpy(float)
    lons = grid["longitude"].to_numpy(float)
    lat0 = np.deg2rad(float(lats.mean()))
    x = lons * 111.32 * np.cos(lat0)
    y = lats * 110.57
    return np.column_stack([x, y])


def add_neighborhood_features(grid: gpd.GeoDataFrame, k: int = NEIGHBORHOOD_K) -> gpd.GeoDataFrame:
    """
    Features de vecindario calculadas con VECINOS GEOGRÁFICOS (KNN, ~8 celdas de 1 km²),
    NO con el bloque de validación.

    Antes se usaba `groupby("spatial_block_id").transform("mean")`, donde
    `spatial_block_id` es exactamente el grupo de `GroupKFold` del entrenamiento. Eso
    convertía la media del vecindario en una "huella" continua del grupo de CV (fuga
    entre la feature y la variable de agrupación). El KNN geográfico elimina ese sesgo.
    """
    from scipy.spatial import cKDTree

    coords = _geo_km(grid)
    n = len(grid)
    kk = max(1, min(k + 1, n))          # +1 para excluir la propia celda del promedio
    tree = cKDTree(coords)
    _, idx = tree.query(coords, k=kk)
    if idx.ndim == 1:
        idx = idx[:, None]
    neigh = idx[:, 1:] if idx.shape[1] > 1 else idx  # sin la propia celda

    def _neighbor_mean(col: str) -> np.ndarray:
        vals = grid[col].to_numpy(float)[neigh]
        with np.errstate(invalid="ignore"):
            return np.nanmean(vals, axis=1)

    grid["temp_vecindad_media"] = np.round(_neighbor_mean("temp_2m"), 1)
    grid["humedad_vecindad_media"] = np.round(_neighbor_mean("humedad_relativa"), 1)
    grid["ndvi_anomaly"] = np.round(grid["ndvi"].to_numpy(float) - _neighbor_mean("ndvi"), 3)
    return grid


def add_wind_encoding(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Codifica la dirección del viento (variable CIRCULAR) como sin/cos.

    Usar los grados crudos (0-360) es incorrecto: 359° y 1° son casi iguales pero
    numéricamente opuestos. La codificación sin/cos resuelve esa discontinuidad.
    """
    ang = np.deg2rad(grid["viento_direccion"].to_numpy(float))
    grid["viento_dir_sin"] = np.round(np.sin(ang), 4)
    grid["viento_dir_cos"] = np.round(np.cos(ang), 4)
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
    # Vecindario por VECINOS GEOGRÁFICOS (KNN), no por bloque de validación (ver
    # add_neighborhood_features). Codificación circular del viento (sin/cos).
    grid = add_neighborhood_features(grid)
    grid = add_wind_encoding(grid)

    # La estacionalidad (mes_sin/mes_cos) sí se conserva como columna informativa,
    # pero NO entra al modelo: con una sola fecha de referencia es constante (std=0)
    # y provocaría un desajuste train/serve. Ver app/model.py:FEATURE_ORDER.
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
    parser.add_argument("--ref-dates", default=None,
                        help="Varias fechas separadas por coma (YYYY-MM-DD) para construir un PANEL MULTI-FECHA, "
                             "p. ej. --ref-dates 2026-08-23,2026-08-30,2026-09-06. Requiere un firms_raw.csv con "
                             "varias fechas (ver fetch_firms.py --start-date).")
    parser.add_argument("--start", default="2026-08-15", help="[Deprecado] La ventana se deriva de --ref-date(s)")
    parser.add_argument("--end", default="2026-09-06", help="[Deprecado] La ventana se deriva de --ref-date(s)")
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

    ref_dates = (
        [d.strip() for d in args.ref_dates.split(",") if d.strip()]
        if args.ref_dates else [args.ref_date]
    )

    frames = []
    for ref_date in ref_dates:
        ref_ts = pd.Timestamp(ref_date)

        # Una etiqueta por fecha: focos reales de los 10 días previos a ref_date.
        if not firms_df.empty and "acq_date" in firms_df.columns:
            win_start = (ref_ts - pd.Timedelta(days=9)).strftime("%Y-%m-%d")
            firms_win = firms_df[
                (firms_df["acq_date"] >= win_start) & (firms_df["acq_date"] <= ref_date)
            ]
        else:
            firms_win = firms_df

        grid_d = build_grid(min_lat, min_lon, max_lat, max_lon)
        print(f"  [{ref_date}] {len(grid_d)} celdas de 1km² generadas")

        grid_d = assign_fires_to_grid(firms_win, grid_d)
        start_d = (ref_ts - pd.Timedelta(days=22)).strftime("%Y-%m-%d")
        grid_d = compute_geospatial_features(
            grid_d, bbox, ref_date, start_d, ref_date, use_real=not args.synthetic
        )
        grid_d["ref_date"] = ref_date
        print(f"  [{ref_date}] Target=1: {int(grid_d['target'].sum())} celdas")
        frames.append(grid_d)

    if len(frames) == 1:
        grid = frames[0]
    else:
        merged = pd.concat(frames, ignore_index=True)
        grid = gpd.GeoDataFrame(merged, geometry="geometry", crs=frames[0].crs)
        print(f"🧱 Panel MULTI-FECHA: {len(ref_dates)} fechas | {len(grid):,} filas totales")

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
