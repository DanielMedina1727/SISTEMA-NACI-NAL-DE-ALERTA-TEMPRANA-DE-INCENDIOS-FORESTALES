"""
Carga el modelo ensemble (LightGBM + XGBoost + RandomForest) entrenado por
`data_pipeline/train_model.py` y expone predict_proba(), explain_prediction()
con SHAP (XAI), la clasificación de riesgo (Verde/Amarillo/Rojo), los umbrales
operativos y el percentil del score.

Este módulo es la FUENTE ÚNICA DE VERDAD de:
  - FEATURE_ORDER / DEFAULT_VALUES (las 21 variables que consume el modelo),
  - compute_physical_features() (VPD, interacción viento×pendiente, índice de sequedad),
  - THRESHOLDS y classify() (el semáforo),
  - score_percentile() (ubicación del score en su distribución),
  - explain_prediction() (explicabilidad SHAP por celda).
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

MODEL_PATH = Path(__file__).parent.parent / "models" / "lightgbm_wildfire.pkl"
_META_PATH = MODEL_PATH.parent / "model_metadata.json"

FEATURE_ORDER = [
    # Variables base (terreno, vegetación, meteorología e infraestructura)
    "pendiente_pct", "ndvi", "dist_carretera_m", "dist_poblado_m",
    "temp_2m", "humedad_relativa", "viento_velocidad",
    # Dirección del viento como variable CIRCULAR (sin/cos) + elevación real
    "viento_dir_sin", "viento_dir_cos", "elevacion_m",
    # Variables temporales (sequía, lluvia acumulada, lags)
    "dias_sin_lluvia", "lluvia_acum_7d", "lluvia_acum_15d",
    "temp_lag1", "humedad_lag1", "ndvi_anomaly",
    # Variables espaciales (vecindario KNN geográfico, no bloque de CV)
    "temp_vecindad_media", "humedad_vecindad_media",
    # Variables físicas compuestas de ignición y combustible (v2.4.0)
    "vpd_kpa", "viento_pendiente", "indice_sequedad",
]

FEATURE_LABELS_ES = {
    "pendiente_pct": "Pendiente del terreno (%)",
    "ndvi": "Vigor de vegetación (NDVI)",
    "dist_carretera_m": "Proximidad a carreteras",
    "dist_poblado_m": "Proximidad a centros poblados",
    "temp_2m": "Temperatura a 2 m (°C)",
    "humedad_relativa": "Humedad relativa (%)",
    "viento_velocidad": "Velocidad del viento (km/h)",
    "viento_dir_sin": "Dirección del viento (componente E-O)",
    "viento_dir_cos": "Dirección del viento (componente N-S)",
    "elevacion_m": "Elevación del terreno (m)",
    "dias_sin_lluvia": "Días consecutivos sin lluvia",
    "lluvia_acum_7d": "Lluvia acumulada (7 días)",
    "lluvia_acum_15d": "Lluvia acumulada (15 días)",
    "temp_lag1": "Temperatura día previo",
    "humedad_lag1": "Humedad día previo",
    "ndvi_anomaly": "Anomalía local de vegetación (NDVI)",
    "temp_vecindad_media": "Temperatura del entorno cercano",
    "humedad_vecindad_media": "Humedad del entorno cercano",
    "vpd_kpa": "Déficit de presión de vapor (VPD)",
    "viento_pendiente": "Interacción viento × pendiente",
    "indice_sequedad": "Índice compuesto de sequedad (FWI simplificado)",
}

# NOTA: `mes_sin`/`mes_cos` se descartaron del modelo mientras el dataset tenga
# una sola fecha de referencia (serían constantes, std = 0). `viento_direccion`
# tampoco entra cruda: se codifica como sin/cos (ver encode_wind_direction).


def compute_physical_features(
    temp_2m,
    humedad_relativa,
    viento_velocidad,
    pendiente_pct,
    dias_sin_lluvia,
) -> tuple:
    """
    Calcula tres variables físicas de inflamabilidad y propagación (acepta
    escalares o arreglos NumPy/Series):
      - vpd_kpa: Déficit de Presión de Vapor (kPa), fórmula de Tetens.
      - viento_pendiente: interacción física viento × pendiente (efecto ladera).
      - indice_sequedad: índice compuesto (VPD × sequía acumulada × viento).
    """
    t = np.asarray(temp_2m, dtype=float)
    rh = np.clip(np.asarray(humedad_relativa, dtype=float), 0.0, 100.0)
    wv = np.maximum(0.0, np.asarray(viento_velocidad, dtype=float))
    sl = np.maximum(0.0, np.asarray(pendiente_pct, dtype=float))
    ds = np.maximum(0.0, np.asarray(dias_sin_lluvia, dtype=float))

    es = 0.6108 * np.exp((17.27 * t) / (t + 237.3))
    vpd = np.maximum(0.0, es * (1.0 - rh / 100.0))
    viento_pendiente = wv * sl / 100.0
    indice_sequedad = vpd * (1.0 + ds / 10.0) * (1.0 + wv / 30.0)

    if vpd.ndim == 0:
        return round(float(vpd), 4), round(float(viento_pendiente), 4), round(float(indice_sequedad), 4)
    return np.round(vpd, 4), np.round(viento_pendiente, 4), np.round(indice_sequedad, 4)


_DEF_VPD, _DEF_VP, _DEF_SEQ = compute_physical_features(22.0, 45.0, 15.0, 12.0, 12.0)

DEFAULT_VALUES = {
    "pendiente_pct": 12.0, "ndvi": 0.45, "dist_carretera_m": 800.0, "dist_poblado_m": 1200.0,
    "temp_2m": 22.0, "humedad_relativa": 45.0, "viento_velocidad": 15.0, "viento_direccion": 45.0,
    "viento_dir_sin": 0.7071, "viento_dir_cos": 0.7071, "elevacion_m": 2500.0,
    "dias_sin_lluvia": 12.0, "lluvia_acum_7d": 15.0, "lluvia_acum_15d": 35.0,
    "temp_lag1": 22.0, "humedad_lag1": 45.0, "ndvi_anomaly": 0.0,
    "temp_vecindad_media": 22.0, "humedad_vecindad_media": 45.0,
    "vpd_kpa": _DEF_VPD, "viento_pendiente": _DEF_VP, "indice_sequedad": _DEF_SEQ,
}


def encode_wind_direction(degrees: float) -> tuple[float, float]:
    """Convierte una dirección de viento (0-360°, 0 = Norte) a (sin, cos)."""
    ang = np.deg2rad(float(degrees) % 360.0)
    return float(np.sin(ang)), float(np.cos(ang))


# ── Umbrales operativos Verde / Amarillo / Rojo ───────────────────────────────
# Metodología: PRESUPUESTO DE ALERTA (Rojo = top 1%, Amarillo = top 5%).
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


def _extract_lgb_estimator(model_obj):
    """Localiza el estimador LightGBM dentro de un VotingClassifier o pipeline."""
    if hasattr(model_obj, "named_estimators_") and "lgb" in model_obj.named_estimators_:
        return model_obj.named_estimators_["lgb"]
    if hasattr(model_obj, "calibrated_classifiers_"):
        base = model_obj.calibrated_classifiers_[0].estimator
        return _extract_lgb_estimator(base)
    return model_obj


class RiskModel:
    def __init__(self, model_path: Path = MODEL_PATH):
        self.model_path = model_path
        self._model = None
        self._explainer = None

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

    def _build_feature_df(self, features: dict) -> pd.DataFrame:
        payload = dict(features or {})

        # Compatibilidad hacia atrás: derivar sin/cos del viento si llega en grados.
        if payload.get("viento_direccion") is not None:
            s, c = encode_wind_direction(payload["viento_direccion"])
            payload.setdefault("viento_dir_sin", s)
            payload.setdefault("viento_dir_cos", c)

        # Derivar features físicas compuestas desde los valores entregados (o defaults).
        def _num(key: str) -> float:
            try:
                return float(payload.get(key, DEFAULT_VALUES[key]))
            except (TypeError, ValueError):
                return float(DEFAULT_VALUES[key])

        vpd, vp, seq = compute_physical_features(
            _num("temp_2m"),
            _num("humedad_relativa"),
            _num("viento_velocidad"),
            _num("pendiente_pct"),
            _num("dias_sin_lluvia"),
        )
        payload.setdefault("vpd_kpa", vpd)
        payload.setdefault("viento_pendiente", vp)
        payload.setdefault("indice_sequedad", seq)

        row = {}
        for k in FEATURE_ORDER:
            val = payload.get(k, DEFAULT_VALUES.get(k, 0.0))
            try:
                row[k] = float(val)
            except (TypeError, ValueError):
                row[k] = float(DEFAULT_VALUES.get(k, 0.0))

        return pd.DataFrame([row])

    def predict_proba(self, features: dict) -> float:
        df = self._build_feature_df(features)
        proba = self.model.predict_proba(df)[0][1]
        return float(proba)

    def explain_prediction(self, features: dict, top_k: int = 3) -> list[dict]:
        """
        Explicabilidad XAI por celda usando SHAP TreeExplainer sobre LightGBM.
        Devuelve los `top_k` factores que más empujaron el riesgo hacia arriba o abajo.
        """
        try:
            import shap

            df = self._build_feature_df(features)
            if self._explainer is None:
                lgb_est = _extract_lgb_estimator(self.model)
                self._explainer = shap.TreeExplainer(lgb_est)
            vals = self._explainer.shap_values(df)
            if isinstance(vals, list) and len(vals) > 1:
                arr = np.asarray(vals[1], dtype=float)[0]
            else:
                arr = np.asarray(vals, dtype=float)
                if arr.ndim == 3:
                    arr = arr[0, :, 1]
                elif arr.ndim == 2:
                    arr = arr[0]

            ranked = sorted(
                zip(FEATURE_ORDER, arr),
                key=lambda item: abs(float(item[1])),
                reverse=True,
            )[:top_k]

            return [
                {
                    "feature": feat,
                    "etiqueta": FEATURE_LABELS_ES.get(feat, feat),
                    "valor": round(float(df[feat].iloc[0]), 4),
                    "impacto_shap": round(float(val), 4),
                    "efecto": "aumenta_riesgo" if float(val) >= 0 else "reduce_riesgo",
                }
                for feat, val in ranked
            ]
        except Exception:
            return []
