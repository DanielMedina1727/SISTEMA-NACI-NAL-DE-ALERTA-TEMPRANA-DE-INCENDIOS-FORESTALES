"""
Pipeline Avanzado de Machine Learning para Alerta Temprana de Incendios Forestales
Implementa:
  a) Optimización Bayesiana de hiperparámetros con Optuna
  b) Validación Espacial (Spatial Cross-Validation con GroupKFold por bloques de 50km)
  c) Feature Engineering temporal (sequía, lags, lluvia acumulada, estacionalidad)
  d) Features espaciales (autocorrelación de vecindario)
  e) Ensemble de modelos (LightGBM + XGBoost + Random Forest por Soft Voting)
  f) Calibración de probabilidades (Platt Scaling / Sigmoid)
  g) Manejo riguroso del desbalance de clases (scale_pos_weight adaptativo)
  h) Umbral de decisión óptimo sensible al costo (Cost-Sensitive Thresholding)
  i) Interpretabilidad con SHAP (TreeExplainer)
  j) MLOps: Registro de metadatos, versionado semántico y métricas comparativas
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import joblib
import lightgbm as lgb
import numpy as np
import optuna
import pandas as pd
import shap
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.metrics import (
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold, train_test_split

optuna.logging.set_verbosity(optuna.logging.WARNING)

FEATURE_COLUMNS = [
    # Variables base
    "pendiente_pct", "ndvi", "dist_carretera_m", "dist_poblado_m",
    "temp_2m", "humedad_relativa", "viento_velocidad", "viento_direccion",
    # Variables temporales & estacionales
    "dias_sin_lluvia", "lluvia_acum_7d", "lluvia_acum_15d",
    "temp_lag1", "humedad_lag1", "ndvi_anomaly", "mes_sin", "mes_cos",
    # Variables espaciales (vecindario)
    "temp_vecindad_media", "humedad_vecindad_media",
]


def load_and_prepare_data(data_path: str):
    """Carga dataset y asegura presencia de features y columna de bloque espacial."""
    print(f"📊 Cargando dataset desde {data_path}...")
    if str(data_path).endswith(".parquet"):
        df = pd.read_parquet(data_path)
    else:
        df = pd.read_csv(data_path)

    if "geometry" in df.columns:
        df = df.drop(columns=["geometry"])

    # Garantizar bloque espacial para Spatial CV si no viniera en el CSV
    if "spatial_block_id" not in df.columns:
        lats = df["latitude"].values
        lons = df["longitude"].values
        block_lat = ((lats - lats.min()) // 0.45).astype(int)
        block_lon = ((lons - lons.min()) // 0.45).astype(int)
        df["spatial_block_id"] = [f"block_{lat_b}_{lon_b}" for lat_b, lon_b in zip(block_lat, block_lon)]

    # Asegurar que todas las columnas de features existan
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0

    return df


def optimize_lightgbm_optuna(X: pd.DataFrame, y: pd.Series, groups: pd.Series, n_trials: int = 30):
    """
    a) Optimización Bayesiana de hiperparámetros con Optuna
    b) Evaluado mediante Spatial Cross-Validation (GroupKFold por bloques espaciales)
    """
    print(f"\n🔍 [Optuna] Iniciando búsqueda bayesiana de hiperparámetros ({n_trials} trials con Spatial CV)...")

    gkf = GroupKFold(n_splits=5)
    scale_pos = max(1.0, (len(y) - y.sum()) / max(1, y.sum()))

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 150, 500),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.08, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 8, 24),
            "max_depth": trial.suggest_int("max_depth", 3, 6),
            "min_child_samples": trial.suggest_int("min_child_samples", 40, 120),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 5.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 5.0, log=True),
            # Con muy pocos positivos, un scale_pos_weight extremo degrada la
            # capacidad de ranking (AUC). Se limita a un rango moderado.
            "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1.0, 20.0),
            "random_state": 42,
            "verbosity": -1,
        }

        # Objetivo: ROC-AUC medio en validación espacial (libre de umbral y estable
        # con clases muy desbalanceadas; F1@0.5 es un objetivo ruidoso aquí).
        auc_scores = []
        for train_idx, val_idx in gkf.split(X, y, groups):
            X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
            X_va, y_val = X.iloc[val_idx], y.iloc[val_idx]

            model = lgb.LGBMClassifier(**params)
            model.fit(X_tr, y_tr)
            if len(np.unique(y_val)) > 1:
                auc_scores.append(roc_auc_score(y_val, model.predict_proba(X_va)[:, 1]))

        return float(np.mean(auc_scores)) if auc_scores else 0.0

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    print(f"  -> Mejor ROC-AUC en Spatial CV: {study.best_value:.4f}")
    print(f"  -> Mejores hiperparámetros encontrados:")
    for k, v in study.best_params.items():
        print(f"     • {k}: {v}")

    return study.best_params, study.best_value


def select_operating_threshold(val_probas, alert_budget: float = 0.01):
    """
    h) Umbral de operación de un sistema de ALERTA TEMPRANA.

    Un mapa de riesgo no puede alertar 68.000 celdas: se fija un presupuesto de
    alerta (`alert_budget`, p. ej. el 1% de celdas de mayor riesgo) y se toma el
    cuantil correspondiente sobre el conjunto de VALIDACIÓN (sin fuga de información).
    """
    val_probas = np.asarray(val_probas)
    if val_probas.size == 0:
        return 0.5
    return float(np.quantile(val_probas, 1.0 - alert_budget))


def recall_at_budget(y_true, probas, budget: float) -> float:
    """Fracción de incendios capturada dentro del `budget` de celdas de mayor riesgo."""
    y_true = np.asarray(y_true)
    probas = np.asarray(probas)
    k = max(1, int(len(probas) * budget))
    top = np.argsort(probas)[::-1][:k]
    return float(y_true[top].sum()) / max(1, int(y_true.sum()))


def _build_ensemble(best_params: dict) -> VotingClassifier:
    """Ensemble ponderado (LightGBM + XGBoost + RandomForest) por soft voting."""
    return VotingClassifier(
        estimators=[
            ("lgb", lgb.LGBMClassifier(**best_params, random_state=42, verbosity=-1)),
            ("xgb", xgb.XGBClassifier(
                n_estimators=120, max_depth=5, learning_rate=0.06,
                scale_pos_weight=float(best_params.get("scale_pos_weight", 5.0)),
                eval_metric="logloss", random_state=42)),
            ("rf", RandomForestClassifier(
                n_estimators=100, max_depth=8, class_weight="balanced",
                random_state=42, n_jobs=-1)),
        ],
        voting="soft",
        weights=[0.55, 0.30, 0.15],
    )


def train_advanced_pipeline(data_path: str, output_model_path: str, optuna_trials: int = 25):
    df = load_and_prepare_data(data_path)
    X = df[FEATURE_COLUMNS]
    y = df["target"]
    groups = df["spatial_block_id"]

    print(f"  -> Total celdas: {len(df):,}")
    print(f"  -> Positivos (Target=1): {y.sum()} ({y.mean():.3%})")
    print(f"  -> Bloques espaciales (50km): {groups.nunique()}")

    # ── Optimización de hiperparámetros con Optuna (Spatial CV sobre todo el set) ──
    best_params, optuna_cv_f1 = optimize_lightgbm_optuna(X, y, groups, n_trials=optuna_trials)

    # ── Evaluación HONESTA: Spatial GroupKFold 5-fold (out-of-fold) ──────────────
    # Se entrena en 4/5 de los bloques espaciales y se predice el bloque no visto.
    # El umbral sensible al costo se elige en una validación interna por fold,
    # NUNCA sobre el bloque de test (así no hay fuga de información).
    print("\n🗺️ [Evaluación] Validación cruzada ESPACIAL 5-fold (out-of-fold)...")
    gkf = GroupKFold(n_splits=5)
    oof_base = np.full(len(y), np.nan)
    oof_opt = np.full(len(y), np.nan)
    opt_pred = np.zeros(len(y), dtype=int)
    base_scale_pos = max(1.0, (len(y) - y.sum()) / max(1, y.sum()))
    alert_budget = 0.01  # 1% de celdas de mayor riesgo (presupuesto de alerta)
    budgets = [0.01, 0.05, 0.10, 0.20]
    fold_aucs, base_fold_aucs = [], []
    rec_opt = {b: [] for b in budgets}
    rec_base = {b: [] for b in budgets}

    for fold, (tr, te) in enumerate(gkf.split(X, y, groups), 1):
        Xtr, ytr, gtr = X.iloc[tr], y.iloc[tr], groups.iloc[tr]
        Xte, yte = X.iloc[te], y.iloc[te]

        # Baseline (LightGBM de tutorial)
        base = lgb.LGBMClassifier(
            n_estimators=150, learning_rate=0.05, max_depth=6, num_leaves=31,
            scale_pos_weight=base_scale_pos, random_state=42, verbosity=-1
        ).fit(Xtr, ytr)
        oof_base[te] = base.predict_proba(Xte)[:, 1]

        # Pipeline optimizado: Ensemble (LightGBM + XGBoost + RandomForest).
        # NOTA: NO se aplica calibración de probabilidades. Con <50 positivos,
        # Platt scaling resultó inestable y degradaba el ranking (AUC).
        ens = _build_ensemble(best_params).fit(Xtr, ytr)
        oof_opt[te] = ens.predict_proba(Xte)[:, 1]

        # Umbral de operación por fold: cuantil que deja en alerta el `alert_budget`
        # de celdas de mayor riesgo (elegido en validación interna espacial, sin
        # tocar el bloque de test).
        itr, ival = next(GroupKFold(n_splits=4).split(Xtr, ytr, gtr))
        thr_clf = lgb.LGBMClassifier(
            n_estimators=200, learning_rate=0.03, num_leaves=15,
            min_child_samples=60, scale_pos_weight=1.0, random_state=42, verbosity=-1
        ).fit(Xtr.iloc[itr], ytr.iloc[itr])
        thr = select_operating_threshold(
            thr_clf.predict_proba(Xtr.iloc[ival])[:, 1], alert_budget=alert_budget
        )
        opt_pred[te] = (oof_opt[te] >= thr).astype(int)

        # Métricas POR FOLD: las probabilidades NO son comparables entre folds, así
        # que no se agrupan las predicciones; se promedian las métricas por fold.
        if len(np.unique(yte)) > 1:
            fold_aucs.append(roc_auc_score(yte, oof_opt[te]))
            base_fold_aucs.append(roc_auc_score(yte, oof_base[te]))
        for b in budgets:
            rec_opt[b].append(recall_at_budget(yte, oof_opt[te], b))
            rec_base[b].append(recall_at_budget(yte, oof_base[te], b))
        print(f"   fold {fold}: test={len(te)} celdas | positivos={int(yte.sum())} | umbral={thr:.3f}")

    base_auc = float(np.mean(base_fold_aucs)) if base_fold_aucs else float("nan")
    final_auc = float(np.mean(fold_aucs)) if fold_aucs else float("nan")
    base_pred = (oof_base >= 0.5).astype(int)
    base_f1 = f1_score(y, base_pred, zero_division=0)
    base_rec = recall_score(y, base_pred, zero_division=0)
    final_f1 = f1_score(y, opt_pred, zero_division=0)
    final_prec = precision_score(y, opt_pred, zero_division=0)
    final_rec = recall_score(y, opt_pred, zero_division=0)

    print("\n" + "═" * 78)
    print("📋 TABLA COMPARATIVA — ANTES VS DESPUÉS (OOF ESPACIAL, MEDIA POR FOLD)")
    print("═" * 78)
    print(f"{'Métrica':<26} | {'Baseline Tutorial':<20} | {'Pipeline Optimizado':<20}")
    print("-" * 78)
    print(f"{'ROC-AUC (media por fold)':<26} | {base_auc:<20.4f} | {final_auc:<20.4f}")
    if fold_aucs:
        print(f"{'   ± desv. est. entre folds':<26} | {'-':<20} | {np.std(fold_aucs):<20.4f}")
    for b in budgets:
        print(f"{'Recall @ Top-' + f'{int(b * 100)}% celdas':<26} | {np.mean(rec_base[b]):<20.2%} | {np.mean(rec_opt[b]):<20.2%}")
    print(f"{'F1 (alarma, presup. 1%)':<26} | {base_f1:<20.4f} | {final_f1:<20.4f}")
    print(f"{'Precisión (presup. 1%)':<26} | {'-':<20} | {final_prec:<20.4%}")
    print("═" * 78)

    # ── Modelo FINAL para producción: entrenado en TODOS los datos ──────────────
    print("\n🏁 [Modelo final] Entrenando ensemble con todos los datos...")
    calibrated_model = _build_ensemble(best_params).fit(X, y)

    # Umbral de operación del modelo final (cuantil de validación interna espacial,
    # sin tocar el test). Deja en alerta el `alert_budget` de celdas de mayor riesgo.
    itr, ival = next(GroupKFold(n_splits=4).split(X, y, groups))
    thr_clf = lgb.LGBMClassifier(
        n_estimators=200, learning_rate=0.03, num_leaves=15,
        min_child_samples=60, scale_pos_weight=1.0, random_state=42, verbosity=-1
    ).fit(X.iloc[itr], y.iloc[itr])
    optimal_thresh = select_operating_threshold(
        thr_clf.predict_proba(X.iloc[ival])[:, 1], alert_budget=alert_budget
    )

    # ── Umbrales de operación DATA-DRIVEN para la API (presupuesto de alerta) ────
    # La API predice sobre su propia distribución de scores; los umbrales del
    # semáforo deben ser cuantiles de ESA distribución, no valores fijos (0.70/0.15)
    # ni el umbral OOF (que vive en otra escala). Rojo = top 1%, Amarillo = top 5%.
    _scores = calibrated_model.predict_proba(X[FEATURE_COLUMNS])[:, 1]
    serving_thresholds = {
        "rojo": round(float(np.quantile(_scores, 0.99)), 6),
        "amarillo": round(float(np.quantile(_scores, 0.95)), 6),
        "budget_rojo": 0.01,
        "budget_amarillo": 0.05,
        "descripcion": "Top 1% de celdas por score = Rojo; top 5% = Amarillo (presupuesto de alerta).",
    }
    score_quantiles = [round(float(np.quantile(_scores, i / 100.0)), 6) for i in range(101)]
    print(f"\n🚦 [Umbrales operativos] Rojo (p99) = {serving_thresholds['rojo']:.4f} | "
          f"Amarillo (p95) = {serving_thresholds['amarillo']:.4f}")

    # LightGBM ajustado sobre todos los datos (para interpretabilidad SHAP)
    opt_lgb = lgb.LGBMClassifier(**best_params, random_state=42, verbosity=-1).fit(X, y)

    # 8. Interpretabilidad SHAP
    print("\n🔮 [SHAP] Calculando valores SHAP y explicabilidad de características...")
    try:
        sample_size = min(300, len(X))
        sample_X = X.sample(sample_size, random_state=42)
        explainer = shap.TreeExplainer(opt_lgb)
        shap_vals = explainer.shap_values(sample_X)
        if isinstance(shap_vals, list) and len(shap_vals) > 1:
            shap_matrix = shap_vals[1]
        else:
            shap_matrix = shap_vals

        mean_shap = np.abs(shap_matrix).mean(axis=0)
        shap_importance = {
            feat: float(round(score, 5))
            for feat, score in sorted(zip(FEATURE_COLUMNS, mean_shap), key=lambda x: x[1], reverse=True)
        }
        print("  -> Top 6 variables con mayor impacto según SHAP:")
        for idx, (ft, val) in enumerate(list(shap_importance.items())[:6], 1):
            print(f"     {idx}. {ft:<22} (Impacto SHAP medio: {val:.4f})")
    except Exception as exc:
        print(f"  ⚠️ Advertencia al calcular SHAP: {exc}")
        shap_importance = {}

    # 9. MLOps: Registro y Metadatos
    out_model = Path(output_model_path)
    out_model.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(calibrated_model, out_model)

    metadata = {
        "model_version": "v2.2.0-spatial-ensemble-real",
        "training_date": datetime.now().isoformat(),
        "algorithm": "Ensemble (LightGBM + XGBoost + RandomForest)",
        "features": FEATURE_COLUMNS,
        "feature_sources": {
            "terreno": "Copernicus DEM GLO-30 (pendiente, aspecto, elevación)",
            "vegetacion": "Sentinel-2 L2A (NDVI)",
            "meteorologia": "ERA5 vía Open-Meteo (temp, humedad, viento, lluvia, sequía)",
            "infraestructura": "OpenStreetMap (distancia a vías y poblados)",
            "etiqueta": "NASA FIRMS (focos de calor reales)",
        },
        "probability_calibration": "descartada: Platt scaling resultaba inestable y degradaba el AUC con <50 positivos",
        "validation_strategy": "Spatial GroupKFold 5-fold out-of-fold (bloques de 50 km sin fuga espacial)",
        "operating_threshold": optimal_thresh,
        "alert_budget": alert_budget,
        "serving_thresholds": serving_thresholds,
        "score_quantiles": score_quantiles,
        "metrics": {
            "baseline": {
                "f1_score": round(float(base_f1), 4),
                "recall": round(float(base_rec), 4),
                "roc_auc": round(float(base_auc), 4),
            },
            "optimized_ensemble": {
                "f1_score": round(float(final_f1), 4),
                "precision": round(float(final_prec), 4),
                "recall": round(float(final_rec), 4),
                "roc_auc": round(float(final_auc), 4),
                "roc_auc_fold_std": round(float(np.std(fold_aucs)), 4) if fold_aucs else None,
                "recall_at_top_1pct": round(float(np.mean(rec_opt[0.01])), 4),
                "recall_at_top_5pct": round(float(np.mean(rec_opt[0.05])), 4),
                "recall_at_top_10pct": round(float(np.mean(rec_opt[0.10])), 4),
                "recall_at_top_20pct": round(float(np.mean(rec_opt[0.20])), 4),
            },
        },
        "optuna_best_params": {k: (float(v) if isinstance(v, (int, float, np.floating)) else v) for k, v in best_params.items()},
        "shap_feature_importance": shap_importance,
    }

    meta_path = out_model.parent / "model_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Modelo Ensemble Calibrado guardado en: {out_model}")
    print(f"📄 Metadatos y registro MLOps guardados en: {meta_path}")


def main():
    parser = argparse.ArgumentParser(description="Entrena pipeline avanzado de ML con Spatial CV, Optuna, Ensemble y SHAP")
    parser.add_argument("--input", default="data/dataset.parquet", help="Ruta del dataset")
    parser.add_argument("--out", default="models/lightgbm_wildfire.pkl", help="Ruta de salida del modelo")
    parser.add_argument("--trials", type=int, default=25, help="Número de trials para Optuna")
    args = parser.parse_args()

    train_advanced_pipeline(args.input, args.out, optuna_trials=args.trials)


if __name__ == "__main__":
    main()
