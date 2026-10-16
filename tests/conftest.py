"""
Configuración común de pytest: hace importable la raíz del proyecto y expone
marcadores para los tests que dependen del modelo/dataset entrenados.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODEL_PATH = ROOT / "models" / "lightgbm_wildfire.pkl"
META_PATH = ROOT / "models" / "model_metadata.json"
DATASET_CSV = ROOT / "data" / "dataset.csv"
DATASET_PARQUET = ROOT / "data" / "dataset.parquet"

requires_model = pytest.mark.skipif(
    not MODEL_PATH.exists(), reason="Modelo no entrenado (models/lightgbm_wildfire.pkl)"
)
requires_metadata = pytest.mark.skipif(
    not META_PATH.exists(), reason="Metadatos del modelo no disponibles"
)
requires_dataset = pytest.mark.skipif(
    not (DATASET_CSV.exists() or DATASET_PARQUET.exists()),
    reason="Dataset no disponible (data/dataset.csv|parquet)",
)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reinicia el rate limiter en memoria antes y después de cada test."""
    try:
        from app.security import reset_rate_limiter
    except Exception:
        yield
        return
    reset_rate_limiter()
    yield
    reset_rate_limiter()
