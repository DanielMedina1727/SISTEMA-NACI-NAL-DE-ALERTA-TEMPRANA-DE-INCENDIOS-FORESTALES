# -*- coding: utf-8 -*-
"""
Recalcula las features derivadas/vecindario del dataset EXISTENTE sin volver a
descargar datos reales (DEM / Sentinel-2 / ERA5 / OSM).

Se usa para propagar dos correcciones metodológicas a un dataset ya generado:

  1. Vecindario por VECINOS GEOGRÁFICOS (KNN) en vez de `groupby(spatial_block_id)`
     -> elimina la fuga entre la feature de vecindario y el grupo de GroupKFold.
  2. Codificación CIRCULAR del viento (viento_dir_sin / viento_dir_cos).

Uso:
    python data_pipeline/refresh_dataset.py
    python data_pipeline/refresh_dataset.py --input data/dataset.parquet --k 8
"""
import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from data_pipeline.grid_builder import (  # noqa: E402
    NEIGHBORHOOD_K,
    add_neighborhood_features,
    add_wind_encoding,
)


def refresh(input_path: str, k: int = NEIGHBORHOOD_K) -> pd.DataFrame:
    in_path = Path(input_path)
    csv_path = in_path.with_suffix(".csv")

    if in_path.exists():
        try:
            df = pd.read_parquet(in_path)
        except Exception:
            df = pd.read_csv(csv_path)
    elif csv_path.exists():
        df = pd.read_csv(csv_path)
    else:
        raise FileNotFoundError(
            f"No se encontró {in_path} ni {csv_path}. "
            "Ejecuta data_pipeline/grid_builder.py primero."
        )

    print(f"📥 Dataset cargado: {len(df):,} filas desde {in_path if in_path.exists() else csv_path}")

    for col in ("latitude", "longitude", "temp_2m", "humedad_relativa", "ndvi", "viento_direccion"):
        if col not in df.columns:
            raise KeyError(f"Falta la columna '{col}', necesaria para recalcular el vecindario.")

    if "elevacion_m" not in df.columns:
        df["elevacion_m"] = 2500.0

    # 1) Vecindario geográfico (KNN)
    df = add_neighborhood_features(df, k=k)
    # 2) Viento sin/cos (circular)
    df = add_wind_encoding(df)

    if in_path.exists():
        df.to_parquet(in_path, index=False)
        print(f"💾 Parquet actualizado: {in_path}")

    # El CSV público se guarda sin la geometría (igual que hace grid_builder.py)
    out_csv = df.drop(columns=["geometry"], errors="ignore")
    out_csv.to_csv(csv_path, index=False)
    print(f"💾 CSV actualizado: {csv_path}")
    print("   - temp_vecindad_media / humedad_vecindad_media / ndvi_anomaly → KNN geográfico")
    print("   - viento_dir_sin / viento_dir_cos → codificación circular")
    return df


def main():
    parser = argparse.ArgumentParser(description="Recalcula features derivadas del dataset sin red")
    parser.add_argument("--input", default="data/dataset.parquet")
    parser.add_argument("--k", type=int, default=NEIGHBORHOOD_K,
                        help="Nº de vecinos geográficos para las medias de vecindario")
    args = parser.parse_args()
    refresh(args.input, k=args.k)


if __name__ == "__main__":
    main()
