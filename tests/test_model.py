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
