"""
Pruebas del pipeline de datos (data_pipeline/grid_builder.py): features de
vecindario por KNN geográfico (sin fuga con el bloque de validación) y
codificación circular del viento.
"""
import numpy as np
import pandas as pd

from app.model import encode_wind_direction
from data_pipeline.grid_builder import add_neighborhood_features, add_wind_encoding


def _mini_grid() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "latitude": [-7.00, -7.01, -7.02, -8.50],
            "longitude": [-78.00, -78.01, -78.02, -78.50],
            "temp_2m": [20.0, 22.0, 24.0, 30.0],
            "humedad_relativa": [60.0, 50.0, 40.0, 20.0],
            "ndvi": [0.5, 0.4, 0.3, 0.1],
            "viento_direccion": [0.0, 90.0, 180.0, 270.0],
        }
    )


def test_neighborhood_features_are_computed():
    out = add_neighborhood_features(_mini_grid(), k=2)
    assert {"temp_vecindad_media", "humedad_vecindad_media", "ndvi_anomaly"} <= set(out.columns)
    assert not out["temp_vecindad_media"].isna().any()
    assert not out["humedad_vecindad_media"].isna().any()


def test_neighborhood_does_not_depend_on_spatial_block():
    """El cálculo debe funcionar sin `spatial_block_id` (ya no se usa el bloque de CV)."""
    grid = _mini_grid()
    assert "spatial_block_id" not in grid.columns
    add_neighborhood_features(grid, k=2)


def test_neighborhood_uses_geographically_close_cells():
    out = add_neighborhood_features(_mini_grid(), k=1)
    # La celda 0 (-7.00,-78.00) es vecina inmediata de la 1 (-7.01,-78.01): temp 22.
    assert out.loc[0, "temp_vecindad_media"] == 22.0
    # La celda aislada (-8.50,-78.50) NO debe tener como vecina a la 0 (temp 20).
    assert out.loc[3, "temp_vecindad_media"] != 20.0


def test_wind_encoding_is_circular():
    out = add_wind_encoding(_mini_grid())
    assert out.loc[0, "viento_dir_sin"] == 0.0
    assert out.loc[0, "viento_dir_cos"] == 1.0
    assert out.loc[1, "viento_dir_sin"] == 1.0
    assert np.isclose(out.loc[1, "viento_dir_cos"], 0.0, atol=1e-6)


def test_encode_wind_direction_matches_pipeline_encoding():
    sin_v, cos_v = encode_wind_direction(270.0)  # 270° => (sin, cos) = (-1, 0)
    assert sin_v == -1.0
    assert np.isclose(cos_v, 0.0, atol=1e-6)
