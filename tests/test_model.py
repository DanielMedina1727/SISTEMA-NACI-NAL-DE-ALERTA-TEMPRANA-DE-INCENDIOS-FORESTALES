"""
Pruebas de la lógica del modelo y del semáforo (app/model.py) y de la coherencia
con los metadatos MLOps (models/model_metadata.json).

No requieren que el modelo esté cargado salvo donde se indique.
"""
import json

import pytest

from conftest import META_PATH, requires_metadata

from app.model import (
    DEFAULT_VALUES,
    FEATURE_ORDER,
    THRESHOLDS,
    classify,
    encode_wind_direction,
    get_thresholds,
    score_percentile,
)


def test_feature_order_has_no_dead_seasonality():
    # mes_sin/mes_cos son constantes con una única fecha de referencia => fuera.
    assert "mes_sin" not in FEATURE_ORDER
    assert "mes_cos" not in FEATURE_ORDER


def test_wind_direction_is_circular():
    # El viento entra codificado como sin/cos, no en grados crudos.
    assert "viento_dir_sin" in FEATURE_ORDER
    assert "viento_dir_cos" in FEATURE_ORDER
    assert "viento_direccion" not in FEATURE_ORDER


def test_every_feature_has_a_default():
    for feat in FEATURE_ORDER:
        assert feat in DEFAULT_VALUES, f"Falta DEFAULT_VALUES para '{feat}'"


def test_classify_uses_operating_thresholds():
    assert classify(THRESHOLDS["rojo"] + 0.01) == "Rojo"
    assert classify(THRESHOLDS["amarillo"] + 0.001) == "Amarillo"
    assert classify(0.0) == "Verde"


def test_threshold_order_is_consistent():
    assert 0 < THRESHOLDS["amarillo"] < THRESHOLDS["rojo"]
    assert get_thresholds() == THRESHOLDS


def test_score_percentile_in_range():
    for proba in (0.0, THRESHOLDS["amarillo"], THRESHOLDS["rojo"], 1.0):
        pct = score_percentile(proba)
        assert pct is None or 0.0 <= pct <= 100.0


def test_encode_wind_direction_known_values():
    assert encode_wind_direction(0.0) == pytest.approx((0.0, 1.0), abs=1e-6)
    assert encode_wind_direction(90.0) == pytest.approx((1.0, 0.0), abs=1e-6)
    assert encode_wind_direction(180.0) == pytest.approx((0.0, -1.0), abs=1e-6)


@requires_metadata
def test_metadata_features_match_model():
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    assert meta["features"] == FEATURE_ORDER, "El modelo y app/model.py usan features distintas"


@requires_metadata
def test_model_beats_random_baseline():
    """Honestidad: el modelo debe superar claramente al azar."""
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    m = meta["metrics"]["optimized_ensemble"]
    prevalence = meta["random_baseline_precision"]

    assert m["roc_auc"] > 0.55, "ROC-AUC demasiado bajo (¿modelo degenerado?)"
    assert m["average_precision"] > prevalence, "El PR-AUC no supera la prevalencia (azar)"


@requires_metadata
def test_metadata_documents_serving_and_oof_thresholds():
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    assert "serving_thresholds" in meta
    assert "oof_thresholds" in meta
    assert meta["serving_thresholds"]["rojo"] > meta["serving_thresholds"]["amarillo"]


def test_physical_features_monotonicity():
    from app.model import compute_physical_features

    vpd_cool, vp_calm, seq_wet = compute_physical_features(15.0, 80.0, 5.0, 5.0, 1.0)
    vpd_hot, vp_windy, seq_dry = compute_physical_features(32.0, 20.0, 35.0, 35.0, 20.0)
    assert vpd_hot > vpd_cool > 0
    assert vp_windy > vp_calm > 0
    assert seq_dry > seq_wet > 0


@requires_metadata
def test_predict_returns_shap_factores_clave():
    from app.model import RiskModel

    m = RiskModel()
    factors = m.explain_prediction({"temp_2m": 32.0, "humedad_relativa": 20.0, "pendiente_pct": 30.0}, top_k=3)
    assert len(factors) == 3
    for item in factors:
        assert {"feature", "etiqueta", "valor", "impacto_shap", "efecto"} <= set(item.keys())
        assert item["efecto"] in {"aumenta_riesgo", "reduce_riesgo"}


def test_apply_live_weather_updates_features_and_physics():
    import pandas as pd
    from app.live_weather import apply_live_weather

    base = pd.DataFrame({
        "latitude": [-7.16, -7.15, -6.50, -5.70],
        "longitude": [-78.51, -78.50, -78.80, -78.81],
        "pendiente_pct": [25.0, 10.0, 15.0, 5.0],
        "temp_2m": [15.0, 15.0, 15.0, 15.0],
        "humedad_relativa": [80.0, 80.0, 80.0, 80.0],
        "viento_velocidad": [5.0, 5.0, 5.0, 5.0],
        "viento_direccion": [0.0, 0.0, 0.0, 0.0],
        "dias_sin_lluvia": [0.0, 0.0, 0.0, 0.0],
    })
    meteo = pd.DataFrame({
        "latitude": [-7.16, -5.70],
        "longitude": [-78.51, -78.81],
        "temp_2m": [28.0, 22.0],
        "humedad_relativa": [30.0, 65.0],
        "viento_velocidad": [18.0, 9.0],
        "viento_direccion": [90.0, 180.0],
        "dias_sin_lluvia": [10, 1],
        "lluvia_acum_7d": [0.0, 18.5],
        "lluvia_acum_15d": [0.5, 42.0],
        "temp_lag1": [27.0, 21.0],
        "humedad_lag1": [32.0, 68.0],
    })

    updated, info = apply_live_weather(base, meteo_df=meteo)
    assert info["source"] == "open-meteo-live"
    assert info["points"] == 2
    assert updated.loc[0, "temp_2m"] > updated.loc[3, "temp_2m"]
    assert updated.loc[0, "vpd_kpa"] > updated.loc[3, "vpd_kpa"] > 0
    assert updated.loc[0, "indice_sequedad"] > updated.loc[3, "indice_sequedad"]
    assert {"viento_dir_sin", "viento_dir_cos", "temp_vecindad_media", "humedad_vecindad_media"} <= set(updated.columns)
