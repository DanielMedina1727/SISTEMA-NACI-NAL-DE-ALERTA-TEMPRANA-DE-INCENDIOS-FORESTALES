"""
Carga el modelo LightGBM entrenado (Semana 6-8) y expone predict_proba(),
la clasificación de riesgo (Verde/Amarillo/Rojo) y los umbrales operativos.
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

MODEL_PATH = Path(__file__).parent.parent / "models" / "lightgbm_wildfire.pkl"
_META_PATH = MODEL_PATH.parent / "model_metadata.json"

FEATURE_ORDER = [
    # Variables base
    "pendiente_pct", "ndvi", "dist_carretera_m", "dist_poblado_m",
    "temp_2m", "humedad_relativa", "viento_velocidad", "viento_direccion",
    # Variables temporales & estacionales
    "dias_sin_lluvia", "lluvia_acum_7d", "lluvia_acum_15d",
    "temp_lag1", "humedad_lag1", "ndvi_anomaly", "mes_sin", "mes_cos",
    # Variables espaciales (vecindario)
    "temp_vecindad_media", "humedad_vecindad_media",
]

DEFAULT_VALUES = {
    "pendiente_pct": 12.0, "ndvi": 0.45, "dist_carretera_m": 800.0, "dist_poblado_m": 1200.0,
    "temp_2m": 22.0, "humedad_relativa": 45.0, "viento_velocidad": 15.0, "viento_direccion": 45.0,
    "dias_sin_lluvia": 12.0, "lluvia_acum_7d": 15.0, "lluvia_acum_15d": 35.0,
    "temp_lag1": 22.0, "humedad_lag1": 45.0, "ndvi_anomaly": 0.0,
    "mes_sin": -1.0, "mes_cos": 0.0,
    "temp_vecindad_media": 22.0, "humedad_vecindad_media": 45.0,
}


# ── Umbrales operativos Verde / Amarillo / Rojo ───────────────────────────────
# Metodología: PRESUPUESTO DE ALERTA (igual que en Defensa Civil real).
#   Rojo     = top 1% de celdas por score del modelo.
#   Amarillo = top 5%.
# Los valores concretos NO son arbitrarios: se calculan en el entrenamiento
# (data_pipeline/train_model.py) como los cuantiles p99/p95 de la distribución
# real de scores que sirve la API, y se guardan en models/model_metadata.json.
_FALLBACK_THRESHOLDS = {"rojo": 0.15, "amarillo": 0.08}


def get_thresholds() -> dict:
    """Devuelve los umbrales operativos (fuente única de verdad del semáforo)."""
    try:
        meta = json.loads(_META_PATH.read_text(encoding="utf-8"))
        st = meta.get("serving_thresholds") or {}
        rojo = float(st.get("rojo", meta.get("operating_threshold", _FALLBACK_THRESHOLDS["rojo"])))
        amarillo = float(st.get("amarillo", rojo * 0.5))
    except Exception:
        return dict(_FALLBACK_THRESHOLDS)
    if rojo <= 0 or amarillo >= rojo:
        return dict(_FALLBACK_THRESHOLDS)
    return {"rojo": rojo, "amarillo": amarillo}


def classify(proba: float) -> str:
    """Clasifica una probabilidad en 'Verde' | 'Amarillo' | 'Rojo'."""
    p = float(proba)
    if p >= THRESHOLDS["rojo"]:
        return "Rojo"
    if p >= THRESHOLDS["amarillo"]:
        return "Amarillo"
    return "Verde"


def _load_score_quantiles() -> list:
    """Cuantiles (0..100) de la distribución de scores, para expresar percentiles."""
    try:
        meta = json.loads(_META_PATH.read_text(encoding="utf-8"))
        q = meta.get("score_quantiles")
        if q and len(q) >= 2:
            return [float(v) for v in q]
    except Exception:
        pass
    return []


THRESHOLDS = get_thresholds()
_SCORE_QUANTILES = _load_score_quantiles()


def score_percentile(proba: float):
    """Percentil (0-100) de una probabilidad frente a la distribución de scores."""
    if not _SCORE_QUANTILES:
        return None
    idx = int(np.searchsorted(_SCORE_QUANTILES, float(proba), side="right"))
    idx = max(0, min(idx, len(_SCORE_QUANTILES) - 1))
    return round(idx / (len(_SCORE_QUANTILES) - 1) * 100, 1)


class RiskModel:
    def __init__(self, model_path: Path = MODEL_PATH):
        self.model_path = model_path
        self._model = None

    @property
    def model(self):
        if self._model is None:
            if not self.model_path.exists():
                raise FileNotFoundError(
                    f"No se encontró el modelo en {self.model_path}. "
                    "Ejecuta data_pipeline/train_model.py primero."
                )
            self._model = joblib.load(self.model_path)
        return self._model

    def predict_proba(self, features: dict) -> float:
        row = {k: float(features.get(k, DEFAULT_VALUES.get(k, 0.0))) for k in FEATURE_ORDER}
        df = pd.DataFrame([row])
        proba = self.model.predict_proba(df)[0][1]  # probabilidad de clase 1 (incendio)
        return float(proba)


def train_placeholder_notebook_reminder():
    pass

