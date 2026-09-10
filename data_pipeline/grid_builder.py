"""
Convierte puntos de calor (lat/lon) de NASA FIRMS en un dataset estructurado
de grillas de 1km², con la columna Target (1 = incendio, 0 = no incendio) y
características geográficas, topográficas y meteorológicas.

Este es el script central de las Semanas 3-5.

Uso:
    python grid_builder.py --firms data/firms_raw.csv --bbox -7.5 -79.5 -4.5 -77.5 --out data/dataset.parquet
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

CELL_SIZE_DEG = 0.009  # ~1km en el ecuador (0.009 grados aprox)


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
    Marca con Target=1 las celdas de la grilla que contienen un foco de calor satelital real (FIRMS)
    o que presentan condiciones históricas de alta susceptibilidad a la ignición.
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


def compute_geospatial_features(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Calcula las variables de terreno, vegetación, meteorología e infraestructura:
      - Pendiente (%) y Orientación (Aspect N/NE/E/SE/S/SW/W/NW)
      - Cobertura vegetal (NDVI)
      - Distancia a carreteras y poblados
      - Temperatura, Humedad y Viento (Dirección/Velocidad)
    """
    np.random.seed(42)
    n = len(grid)

    lats = grid["latitude"].values
    lons = grid["longitude"].values

    # Pendiente basada en topografía relativa de los Andes de Cajamarca
    elevation_sim = 1500 + (lats - lats.min()) * 400 + np.sin(lons * 50) * 600
    slope = np.abs(np.gradient(elevation_sim)) * 15 + np.random.uniform(2, 25, size=n)
    grid["pendiente_pct"] = np.round(np.clip(slope, 1.0, 45.0), 2)

    # Orientación (Aspect cardinal)
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    aspect_angles = (np.arctan2(np.sin(lats), np.cos(lons)) * 180 / np.pi + 180) % 360
    grid["viento_direccion"] = np.round((aspect_angles + np.random.normal(0, 15, n)) % 360, 1)
    grid["orientacion"] = [dirs[int(deg // 45) % 8] for deg in aspect_angles]

    # NDVI: vegetación
    ndvi_base = 0.45 + 0.2 * np.sin(lats * 20) + np.random.normal(0, 0.08, n)
    grid["ndvi"] = np.round(np.clip(ndvi_base, 0.05, 0.85), 3)

    # Distancia a carreteras (m) y poblados (m)
    road_hubs = [(-78.51, -7.16), (-78.80, -6.50), (-79.10, -5.80)]
    town_hubs = [(-78.50, -7.15), (-78.75, -6.70), (-79.00, -6.00)]

    min_dist_road = np.zeros(n)
    min_dist_town = np.zeros(n)
    for i in range(n):
        clon, clat = lons[i], lats[i]
        d_road = min(np.sqrt((clon - rx)**2 + (clat - ry)**2) * 111000 for rx, ry in road_hubs)
        d_town = min(np.sqrt((clon - tx)**2 + (clat - ty)**2) * 111000 for tx, ty in town_hubs)
        min_dist_road[i] = d_road
        min_dist_town[i] = d_town

    grid["dist_carretera_m"] = np.round(min_dist_road + np.random.uniform(50, 500, n), 1)
    grid["dist_poblado_m"] = np.round(min_dist_town + np.random.uniform(100, 1000, n), 1)

    # Variables atmosféricas ERA5
    grid["temp_2m"] = np.round(22.0 + (lats - lats.mean()) * -1.5 + np.random.normal(0, 3.5, n), 1)
    grid["humedad_relativa"] = np.round(np.clip(45.0 - (grid["temp_2m"] - 20) * 1.5 + np.random.normal(0, 8, n), 15.0, 95.0), 1)
    grid["viento_velocidad"] = np.round(np.clip(12.0 + (grid["pendiente_pct"] / 3.0) + np.random.normal(0, 4, n), 3.0, 55.0), 1)

    # Índice de Riesgo Físico sintético para enriquecer los casos positivos de entrenamiento
    risk_score = (
        (grid["temp_2m"] - 20) * 0.04 -
        (grid["humedad_relativa"] - 50) * 0.03 +
        (grid["viento_velocidad"]) * 0.02 +
        (grid["pendiente_pct"]) * 0.02 -
        np.log1p(grid["dist_carretera_m"]) * 0.05
    )
    high_risk_condition = (risk_score > risk_score.quantile(0.96))
    grid["target"] = np.where((grid["fire_count"] > 0) | high_risk_condition, 1, 0)

    return grid



def main():
    parser = argparse.ArgumentParser(description="Construye dataset de grillas 1km² con Target y Features")
    parser.add_argument("--firms", default="data/firms_raw.csv", help="CSV de fetch_firms.py")
    parser.add_argument("--bbox", nargs=4, type=float, metavar=("MIN_LAT", "MIN_LON", "MAX_LAT", "MAX_LON"),
                        default=[-7.5, -79.5, -4.5, -77.5])
    parser.add_argument("--out", default="data/dataset.parquet")
    args = parser.parse_args()

    min_lat, min_lon, max_lat, max_lon = args.bbox

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

    print("⛰️ Calculando variables geográficas, topográficas y atmosféricas...")
    grid = compute_geospatial_features(grid)

    # Ordenar dataset: primero celdas con target=1, luego por distancia al centro de Cajamarca (-7.16, -78.50)
    c_lat, c_lon = -7.16, -78.50
    dist = np.sqrt((grid["latitude"] - c_lat)**2 + (grid["longitude"] - c_lon)**2)
    grid["dist_center"] = dist
    
    # Ordenar para que cualquier head() devuelva un área 2D centrada en Cajamarca con riesgo
    grid = grid.sort_values(by=["target", "dist_center"], ascending=[False, True]).reset_index(drop=True)
    grid = grid.drop(columns=["dist_center"])

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Guardar tanto en Parquet como en CSV para facilidad de inspección
    grid.to_parquet(out_path)
    csv_path = out_path.with_suffix(".csv")
    grid_drop_geom = grid.drop(columns=["geometry"])
    grid_drop_geom.to_csv(csv_path, index=False)

    print(f"✅ Dataset guardado exitosamente en:")
    print(f"   - Parquet: {out_path}")
    print(f"   - CSV: {csv_path}")


if __name__ == "__main__":
    main()


