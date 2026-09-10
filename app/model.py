"""
Carga el modelo LightGBM entrenado (Semana 6-8) y expone predict_proba().
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

MODEL_PATH = Path(__file__).parent.parent / "models" / "lightgbm_wildfire.pkl"

FEATURE_ORDER = [
    "pendiente_pct", "ndvi", "dist_carretera_m", "dist_poblado_m",
    "temp_2m", "humedad_relativa", "viento_velocidad", "viento_direccion",
]


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
        row = {k: float(features.get(k, 0.0)) for k in FEATURE_ORDER}
        df = pd.DataFrame([row])
        proba = self.model.predict_proba(df)[0][1]  # probabilidad de clase 1 (incendio)
        return float(proba)


def train_placeholder_notebook_reminder():
    pass

