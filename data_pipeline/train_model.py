"""
Pipeline Avanzado de Machine Learning para Alerta Temprana de Incendios Forestales (v2.4.0)
Implementa:
  a) Optimización Bayesiana con Optuna para LightGBM + XGBoost (objetivo compuesto:
     ROC-AUC + PR-AUC normalizado + Recall@Top-10% para desbalance extremo)
  b) Validación Espacial Estratificada (StratifiedGroupKFold 5-fold por bloques de 50 km)
  c) Feature Engineering físico (VPD, interacción viento×pendiente, índice de sequedad),
     temporal (sequía, lags, lluvia acumulada) y espacial (vecindario KNN geográfico)
  d) Optimización de pesos del Ensemble (LightGBM + XGBoost + Random Forest) sobre OOF
  e) Umbrales operativos por presupuesto de alerta (Top-1% Rojo / Top-5% Amarillo)
  f) Explicabilidad XAI con SHAP (TreeExplainer global y por celda en /predict)
  g) MLOps: Registro completo de metadatos, versionado semántico y comparativa honesta
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
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold

optuna.logging.set_verbosity(optuna.logging.WARNING)

# Fuente única de verdad de las features: app/model.py
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app.model import FEATURE_ORDER as FEATURE_COLUMNS  # noqa: E402
from app.model import compute_physical_features  # noqa: E402


def _make_spatial_cv(y: pd.Series, groups: pd.Series, n_splits: int = 5):
    """Usa StratifiedGroupKFold cuando hay suficientes positivos por grupo."""
    n_pos_groups = int(groups[y == 1].nunique())
    if n_pos_groups >= n_splits:
        return StratifiedGroupKFold(n_splits=n_splits)
    return GroupKFold(n_splits=n_splits)


def load_and_prepare_data(data_path: str):
    """Carga dataset y asegura presencia de las 21 features y bloques espaciales."""
    print(f"📊 Cargando dataset desde {data_path}...")
    if str(data_path).endswith(".parquet"):
        df = pd.read_parquet(data_path)
    else:
        df = pd.read_csv(data_path)

    if "geometry" in df.columns:
        df = df.drop(columns=["geometry"])

    if "spatial_block_id" not in df.columns:
        lats = df["latitude"].values
        lons = df["longitude"].values
        block_lat = ((lats - lats.min()) // 0.45).astype(int)
        block_lon = ((lons - lons.min()) // 0.45).astype(int)
        df["spatial_block_id"] = [f"block_{lat_b}_{lon_b}" for lat_b, lon_b in zip(block_lat, block_lon)]

    # Garantizar features físicas compuestas si el parquet aún no las tuviera
    if any(c not in df.columns for c in ("vpd_kpa", "viento_pendiente", "indice_sequedad")):
        vpd, vp, seq = compute_physical_features(
            df.get("temp_2m", 20.0),
            df.get("humedad_relativa", 50.0),
            df.get("viento_velocidad", 10.0),
            df.get("pendiente_pct", 10.0),
            df.get("dias_sin_lluvia", 10.0),
        )
        df["vpd_kpa"] = vpd
        df["viento_pendiente"] = vp
        df["indice_sequedad"] = seq

    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0

    return df


def recall_at_budget(y_true, probas, budget: float) -> float:
    """Fracción de incendios capturada dentro del `budget` de celdas de mayor riesgo."""
    y_true = np.asarray(y_true)
    probas = np.asarray(probas)
    k = max(1, int(len(probas) * budget))
    top = np.argsort(probas)[::-1][:k]
    return float(y_true[top].sum()) / max(1, int(y_true.sum()))


def _composite_ranking_score(y_true, probas) -> float:
    """
    Métrica compuesta para Optuna orientada a alerta temprana con desbalance extremo:
      - 50 % ROC-AUC (ordenamiento global)
      - 30 % PR-AUC relativo a 5× la prevalencia (concentración de positivos arriba)
      - 20 % Recall@Top-10% (utilidad operativa directa del mapa)
    """
    y_arr = np.asarray(y_true)
    p_arr = np.asarray(probas)
    if len(np.unique(y_arr)) < 2:
        return 0.0
    prev = max(float(y_arr.mean()), 1e-6)
    auc = float(roc_auc_score(y_arr, p_arr))
    ap = float(average_precision_score(y_arr, p_arr))
    ap_norm = min(1.0, ap / (5.0 * prev))
    rec10 = recall_at_budget(y_arr, p_arr, 0.10)
    return 0.50 * auc + 0.30 * ap_norm + 0.20 * rec10


def optimize_lightgbm_optuna(X: pd.DataFrame, y: pd.Series, groups: pd.Series, n_trials: int = 25):
    """Optimización bayesiana de LightGBM con validación espacial estratificada."""
    print(f"\n🔍 [Optuna · LightGBM] Búsqueda bayesiana ({n_trials} trials, Spatial StratifiedGroupKFold)...")
    cv = _make_spatial_cv(y, groups, n_splits=5)
    splits = list(cv.split(X, y, groups))

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 120, 450),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.08, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 7, 24),
            "max_depth": trial.suggest_int("max_depth", 3, 6),
            "min_child_samples": trial.suggest_int("min_child_samples", 40, 140),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.55, 1.0),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "subsample_freq": 1,
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 8.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-2, 10.0, log=True),
            "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1.0, 20.0),
            "random_state": 42,
            "verbosity": -1,
            "n_jobs": -1,
        }
        scores = []
        for tr_idx, va_idx in splits:
            model = lgb.LGBMClassifier(**params)
            model.fit(X.iloc[tr_idx], y.iloc[tr_idx])
            probas = model.predict_proba(X.iloc[va_idx])[:, 1]
            scores.append(_composite_ranking_score(y.iloc[va_idx], probas))
        return float(np.mean(scores)) if scores else 0.0

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    print(f"  -> Mejor score compuesto LightGBM: {study.best_value:.4f}")
    return study.best_params, float(study.best_value)


def optimize_xgboost_optuna(X: pd.DataFrame, y: pd.Series, groups: pd.Series, n_trials: int = 15):
    """Optimización bayesiana de XGBoost con validación espacial estratificada."""
    print(f"\n🔍 [Optuna · XGBoost] Búsqueda bayesiana ({n_trials} trials, Spatial StratifiedGroupKFold)...")
    cv = _make_spatial_cv(y, groups, n_splits=5)
    splits = list(cv.split(X, y, groups))

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 350),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.08, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 6),
            "min_child_weight": trial.suggest_float("min_child_weight", 5.0, 40.0),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.55, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 5.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 10.0, log=True),
            "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1.0, 20.0),
            "eval_metric": "logloss",
            "random_state": 42,
            "n_jobs": -1,
        }
        scores = []
        for tr_idx, va_idx in splits:
            model = xgb.XGBClassifier(**params)
            model.fit(X.iloc[tr_idx], y.iloc[tr_idx])
            probas = model.predict_proba(X.iloc[va_idx])[:, 1]
            scores.append(_composite_ranking_score(y.iloc[va_idx], probas))
        return float(np.mean(scores)) if scores else 0.0

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=43))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    print(f"  -> Mejor score compuesto XGBoost: {study.best_value:.4f}")
    return study.best_params, float(study.best_value)


def optimize_ensemble_weights(
    y: pd.Series,
    oof_lgb: np.ndarray,
    oof_xgb: np.ndarray,
    oof_rf: np.ndarray,
    splits: list,
) -> list[float]:
    """Optimiza los pesos [w_lgb, w_xgb, w_rf] del soft voting sobre predicciones OOF."""
    best_w = [0.50, 0.35, 0.15]
    best_score = -1.0
    # Rejilla determinista en simplex (paso 0.05) -> rápido y reproducible
    for w_lgb in np.linspace(0.20, 0.75, 12):
        for w_xgb in np.linspace(0.15, 0.70, 12):
            w_rf = round(1.0 - w_lgb - w_xgb, 4)
            if w_rf < 0.05 or w_rf > 0.40:
                continue
            blend = w_lgb * oof_lgb + w_xgb * oof_xgb + w_rf * oof_rf
            fold_scores = [_composite_ranking_score(y.iloc[te], blend[te]) for _, te in splits]
            sc = float(np.mean(fold_scores))
            if sc > best_score:
                best_score = sc
                best_w = [round(float(w_lgb), 2), round(float(w_xgb), 2), round(float(w_rf), 2)]
    # Normalizar suma exacta a 1.0
    s = sum(best_w)
    best_w = [round(w / s, 3) for w in best_w]
    print(f"⚖️ [Ensemble] Pesos óptimos OOF (LGB/XGB/RF): {best_w} (score={best_score:.4f})")
    return best_w


def select_operating_threshold(val_probas, alert_budget: float = 0.01):
    """Umbral operativo por presupuesto de alerta (top `alert_budget` de celdas)."""
    val_probas = np.asarray(val_probas)
    if val_probas.size == 0:
        return 0.5
    return float(np.quantile(val_probas, 1.0 - alert_budget))


def _build_ensemble(
    lgb_params: dict,
    xgb_params: dict,
    weights: list[float] | None = None,
) -> VotingClassifier:
    """Ensemble ponderado (LightGBM + XGBoost + RandomForest) por soft voting."""
    return VotingClassifier(
        estimators=[
            ("lgb", lgb.LGBMClassifier(**lgb_params, subsample_freq=1, random_state=42, verbosity=-1, n_jobs=-1)),
            ("xgb", xgb.XGBClassifier(**xgb_params, eval_metric="logloss", random_state=42, n_jobs=-1)),
            ("rf", RandomForestClassifier(
                n_estimators=150, max_depth=8, min_samples_leaf=20,
                class_weight="balanced", random_state=42, n_jobs=-1,
            )),
        ],
        voting="soft",
        weights=weights or [0.50, 0.35, 0.15],
    )


def _downsample_for_optuna(X: pd.DataFrame, y: pd.Series, groups: pd.Series, max_rows: int = 180_000):
    """
    Si el panel multi-fecha supera `max_rows`, conserva el 100 % de los positivos y
    muestrea negativos de forma uniforme para acelerar la búsqueda de hiperparámetros
    en Optuna (la CV final y el modelo de producción usan el 100 % de los datos).
    """
    if len(X) <= max_rows:
        return X, y, groups
    pos_idx = np.flatnonzero(y.to_numpy() == 1)
    neg_idx = np.flatnonzero(y.to_numpy() == 0)
    rng = np.random.default_rng(42)
    n_neg = max(len(pos_idx) * 20, max_rows - len(pos_idx))
    sel_neg = rng.choice(neg_idx, size=min(len(neg_idx), n_neg), replace=False)
    sel = np.sort(np.concatenate([pos_idx, sel_neg]))
    return X.iloc[sel].reset_index(drop=True), y.iloc[sel].reset_index(drop=True), groups.iloc[sel].reset_index(drop=True)


def train_advanced_pipeline(
    data_path: str,
    output_model_path: str,
    optuna_trials: int = 25,
    serve_dataset_path: str | None = None,
):
    df = load_and_prepare_data(data_path)
    X = df[FEATURE_COLUMNS]
    y = df["target"]
    groups = df["spatial_block_id"]
    n_dates = int(df["ref_date"].nunique()) if "ref_date" in df.columns else 1
    is_multidate = n_dates > 1

    print(f"  -> Total filas: {len(df):,} ({n_dates} fecha(s) de referencia)")
    print(f"  -> Variables predictoras: {len(FEATURE_COLUMNS)}")
    print(f"  -> Positivos (Target=1): {int(y.sum()):,} ({y.mean():.3%})")
    print(f"  -> Bloques espaciales (50km): {groups.nunique()}")

    # ── 1) Optimización bayesiana Optuna para LightGBM y XGBoost ─────────────
    X_opt, y_opt, g_opt = _downsample_for_optuna(X, y, groups)
    lgb_params, _ = optimize_lightgbm_optuna(X_opt, y_opt, g_opt, n_trials=optuna_trials)
    xgb_params, _ = optimize_xgboost_optuna(X_opt, y_opt, g_opt, n_trials=max(10, optuna_trials // 2))

    # ── 2) Evaluación HONESTA: StratifiedGroupKFold 5-fold (OOF espacial) ────
    print("\n🗺️ [Evaluación] Validación cruzada ESPACIAL estratificada 5-fold (out-of-fold)...")
    cv = _make_spatial_cv(y, groups, n_splits=5)
    splits = list(cv.split(X, y, groups))

    oof_base = np.full(len(y), np.nan)
    oof_lgb = np.full(len(y), np.nan)
    oof_xgb = np.full(len(y), np.nan)
    oof_rf = np.full(len(y), np.nan)
    base_scale_pos = max(1.0, (len(y) - y.sum()) / max(1, y.sum()))
    alert_budget = 0.01
    budgets = [0.01, 0.05, 0.10, 0.20]

    for fold, (tr, te) in enumerate(splits, 1):
        Xtr, ytr = X.iloc[tr], y.iloc[tr]
        Xte, yte = X.iloc[te], y.iloc[te]

        # Baseline (LightGBM de tutorial sin regularización ni ajuste espacial)
        base = lgb.LGBMClassifier(
            n_estimators=150, learning_rate=0.05, max_depth=6, num_leaves=31,
            scale_pos_weight=base_scale_pos, random_state=42, verbosity=-1, n_jobs=-1,
        ).fit(Xtr, ytr)
        oof_base[te] = base.predict_proba(Xte)[:, 1]

        # Estimadores individuales del ensemble en este fold
        m_lgb = lgb.LGBMClassifier(**lgb_params, subsample_freq=1, random_state=42, verbosity=-1, n_jobs=-1).fit(Xtr, ytr)
        m_xgb = xgb.XGBClassifier(**xgb_params, eval_metric="logloss", random_state=42, n_jobs=-1).fit(Xtr, ytr)
        m_rf = RandomForestClassifier(
            n_estimators=150, max_depth=8, min_samples_leaf=20,
            class_weight="balanced", random_state=42, n_jobs=-1,
        ).fit(Xtr, ytr)

        oof_lgb[te] = m_lgb.predict_proba(Xte)[:, 1]
        oof_xgb[te] = m_xgb.predict_proba(Xte)[:, 1]
        oof_rf[te] = m_rf.predict_proba(Xte)[:, 1]
        print(f"   fold {fold}: test={len(te)} celdas | positivos={int(yte.sum())}")

    # Optimizar pesos del ensemble sobre las probabilidades OOF
    ens_weights = optimize_ensemble_weights(y, oof_lgb, oof_xgb, oof_rf, splits)
    oof_opt = ens_weights[0] * oof_lgb + ens_weights[1] * oof_xgb + ens_weights[2] * oof_rf

    fold_aucs, base_fold_aucs = [], []
    fold_ap, base_fold_ap = [], []
    rec_opt = {b: [] for b in budgets}
    rec_base = {b: [] for b in budgets}
    opt_pred = np.zeros(len(y), dtype=int)

    for tr, te in splits:
        yte = y.iloc[te]
        # Umbral de alerta por fold estimado sobre los scores OOF del bloque de entrenamiento
        thr = select_operating_threshold(oof_opt[tr], alert_budget=alert_budget)
        opt_pred[te] = (oof_opt[te] >= thr).astype(int)

        if len(np.unique(yte)) > 1:
            fold_aucs.append(roc_auc_score(yte, oof_opt[te]))
            base_fold_aucs.append(roc_auc_score(yte, oof_base[te]))
            fold_ap.append(average_precision_score(yte, oof_opt[te]))
            base_fold_ap.append(average_precision_score(yte, oof_base[te]))
        for b in budgets:
            rec_opt[b].append(recall_at_budget(yte, oof_opt[te], b))
            rec_base[b].append(recall_at_budget(yte, oof_base[te], b))

    base_auc = float(np.mean(base_fold_aucs)) if base_fold_aucs else float("nan")
    final_auc = float(np.mean(fold_aucs)) if fold_aucs else float("nan")
    base_ap = float(np.mean(base_fold_ap)) if base_fold_ap else float("nan")
    final_ap = float(np.mean(fold_ap)) if fold_ap else float("nan")
    base_pred = (oof_base >= 0.5).astype(int)
    base_f1 = f1_score(y, base_pred, zero_division=0)
    base_rec = recall_score(y, base_pred, zero_division=0)
    final_f1 = f1_score(y, opt_pred, zero_division=0)
    final_prec = precision_score(y, opt_pred, zero_division=0)
    final_rec = recall_score(y, opt_pred, zero_division=0)

    print("\n" + "═" * 78)
    print("📋 TABLA COMPARATIVA — ANTES VS DESPUÉS (OOF ESPACIAL ESTRATIFICADO)")
    print("═" * 78)
    print(f"{'Métrica':<26} | {'Baseline Tutorial':<20} | {'Ensemble v2.4.0':<20}")
    print("-" * 78)
    print(f"{'ROC-AUC (media por fold)':<26} | {base_auc:<20.4f} | {final_auc:<20.4f}")
    if fold_aucs:
        print(f"{'   ± desv. est. entre folds':<26} | {'-':<20} | {np.std(fold_aucs):<20.4f}")
    print(f"{'PR-AUC (Average Precision)':<26} | {base_ap:<20.4f} | {final_ap:<20.4f}")
    print(f"{'   (azar ≈ prevalencia)':<26} | {y.mean():<20.5f} | {y.mean():<20.5f}")
    for b in budgets:
        print(f"{'Recall @ Top-' + f'{int(b * 100)}% celdas':<26} | {np.mean(rec_base[b]):<20.2%} | {np.mean(rec_opt[b]):<20.2%}")
    print(f"{'F1 (alarma, presup. 1%)':<26} | {base_f1:<20.4f} | {final_f1:<20.4f}")
    print(f"{'Precisión (presup. 1%)':<26} | {'-':<20} | {final_prec:<20.4%}")
    print("═" * 78)

    # ── 2B) Validación TEMPORAL estricta (si el panel tiene múltiples años) ──
    temporal_metrics = None
    if is_multidate and "year" in df.columns and df["year"].nunique() >= 2:
        test_year = int(df["year"].max())
        tr_mask = df["year"] < test_year
        te_mask = df["year"] == test_year
        if int(y[tr_mask].sum()) >= 20 and int(y[te_mask].sum()) >= 5:
            print(f"\n⏳ [Validación Temporal] Entrenando < {test_year} -> Evaluando temporada futura {test_year}...")
            temp_ens = _build_ensemble(lgb_params, xgb_params, weights=ens_weights).fit(X[tr_mask], y[tr_mask])
            p_temp = temp_ens.predict_proba(X[te_mask])[:, 1]
            y_temp = y[te_mask]
            t_auc = float(roc_auc_score(y_temp, p_temp))
            t_ap = float(average_precision_score(y_temp, p_temp))
            temporal_metrics = {
                "train_years": sorted(int(v) for v in df.loc[tr_mask, "year"].unique()),
                "test_year": test_year,
                "test_rows": int(te_mask.sum()),
                "test_positives": int(y_temp.sum()),
                "test_prevalence": round(float(y_temp.mean()), 5),
                "roc_auc": round(t_auc, 4),
                "average_precision": round(t_ap, 4),
                "recall_at_top_1pct": round(recall_at_budget(y_temp, p_temp, 0.01), 4),
                "recall_at_top_5pct": round(recall_at_budget(y_temp, p_temp, 0.05), 4),
                "recall_at_top_10pct": round(recall_at_budget(y_temp, p_temp, 0.10), 4),
                "recall_at_top_20pct": round(recall_at_budget(y_temp, p_temp, 0.20), 4),
            }
            print(
                f"   -> Temporada {test_year} ({temporal_metrics['test_positives']} positivos): "
                f"ROC-AUC={t_auc:.4f} | PR-AUC={t_ap:.4f} | "
                f"Top-5%={temporal_metrics['recall_at_top_5pct']:.1%} | "
                f"Top-10%={temporal_metrics['recall_at_top_10pct']:.1%} | "
                f"Top-20%={temporal_metrics['recall_at_top_20pct']:.1%}"
            )

    # ── 3) Modelo FINAL para producción ──────────────────────────────────────
    print("\n🏁 [Modelo final] Entrenando ensemble con todos los datos...")
    final_model = _build_ensemble(lgb_params, xgb_params, weights=ens_weights).fit(X, y)

    optimal_thresh = select_operating_threshold(oof_opt, alert_budget=alert_budget)

    # Si entrenamos en panel multi-fecha, calcular los cuantiles del semáforo sobre
    # el snapshot servido por la API (data/dataset.parquet) para consistencia exacta.
    if serve_dataset_path and Path(serve_dataset_path).exists():
        serve_df = load_and_prepare_data(serve_dataset_path)
        _scores = final_model.predict_proba(serve_df[FEATURE_COLUMNS])[:, 1]
    else:
        _scores = final_model.predict_proba(X[FEATURE_COLUMNS])[:, 1]
    serving_thresholds = {
        "rojo": round(float(np.quantile(_scores, 0.99)), 6),
        "amarillo": round(float(np.quantile(_scores, 0.95)), 6),
        "budget_rojo": 0.01,
        "budget_amarillo": 0.05,
        "descripcion": (
            "Cuantiles de la distribución de scores SERVIDA (in-sample): Rojo = top 1% "
            "del ranking, Amarillo = top 5%. Criterio de RANKING relativo (presupuesto de alerta)."
        ),
    }
    score_quantiles = [round(float(np.quantile(_scores, i / 100.0)), 6) for i in range(101)]

    oof_thresholds = {
        "rojo": round(float(np.nanquantile(oof_opt, 0.99)), 6),
        "amarillo": round(float(np.nanquantile(oof_opt, 0.95)), 6),
        "nota": "Cuantiles de los scores OUT-OF-FOLD (referencia honesta sin optimismo in-sample).",
    }
    print(
        f"\n🚦 [Umbrales operativos] Rojo (p99) = {serving_thresholds['rojo']:.4f} | "
        f"Amarillo (p95) = {serving_thresholds['amarillo']:.4f}"
    )

    # ── 4) Interpretabilidad global SHAP (TreeExplainer) ─────────────────────
    print("\n🔮 [SHAP] Calculando importancia global SHAP...")
    try:
        opt_lgb = final_model.named_estimators_["lgb"]
        sample_size = min(500, len(X))
        sample_X = X.sample(sample_size, random_state=42)
        explainer = shap.TreeExplainer(opt_lgb)
        shap_vals = explainer.shap_values(sample_X)
        if isinstance(shap_vals, list) and len(shap_vals) > 1:
            shap_matrix = shap_vals[1]
        else:
            shap_matrix = np.asarray(shap_vals)
            if shap_matrix.ndim == 3:
                shap_matrix = shap_matrix[:, :, 1]

        mean_shap = np.abs(shap_matrix).mean(axis=0)
        shap_importance = {
            feat: float(round(score, 5))
            for feat, score in sorted(zip(FEATURE_COLUMNS, mean_shap), key=lambda x: x[1], reverse=True)
        }
        print("  -> Top 8 variables con mayor impacto según SHAP:")
        for idx, (ft, val) in enumerate(list(shap_importance.items())[:8], 1):
            print(f"     {idx}. {ft:<24} (Impacto SHAP medio: {val:.4f})")
    except Exception as exc:
        print(f"  ⚠️ Advertencia al calcular SHAP: {exc}")
        shap_importance = {}

    # ── 5) MLOps: Guardar modelo y metadatos ─────────────────────────────────
    out_model = Path(output_model_path)
    out_model.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, out_model)

    model_ver = "v2.5.0-multidate-spatial-temporal-xai" if is_multidate else "v2.4.0-spatial-ensemble-xai"
    metadata = {
        "model_version": model_ver,
        "training_date": datetime.now().isoformat(),
        "training_rows": int(len(df)),
        "training_positives": int(y.sum()),
        "training_ref_dates": sorted(str(d) for d in df["ref_date"].unique()) if "ref_date" in df.columns else [],
        "algorithm": "Ensemble (LightGBM + XGBoost + RandomForest)",
        "ensemble_weights": {"lgb": ens_weights[0], "xgb": ens_weights[1], "rf": ens_weights[2]},
        "task": "Índice de SUSCEPTIBILIDAD diario (ranking relativo) con explicabilidad SHAP",
        "features": FEATURE_COLUMNS,
        "feature_sources": {
            "terreno": "Copernicus DEM GLO-30 (pendiente, aspecto, elevación)",
            "vegetacion": "Sentinel-2 L2A mosaico multi-tesela MGRS (NDVI corregido)",
            "meteorologia": "ERA5 vía Open-Meteo (temp, humedad, viento, lluvia, sequía, VPD, FWI)",
            "infraestructura": "OpenStreetMap (distancia a vías y poblados)",
            "etiqueta": "NASA FIRMS histórico multi-fecha (VIIRS_SNPP_SP + VIIRS_SNPP_NRT)",
        },
        "feature_engineering": (
            "Panel multi-fecha real (temporadas secas 2024–2026), NDVI Sentinel-2 corregido "
            "(99.48% cobertura real), vecindario KNN geográfico, viento circular (sin/cos) y "
            "3 variables físicas compuestas: vpd_kpa (Tetens), viento_pendiente e indice_sequedad."
        ),
        "optuna_objective": "0.50*ROC_AUC + 0.30*min(1, PR_AUC/(5*prevalencia)) + 0.20*Recall@Top10%",
        "probability_calibration": "ranking por presupuesto de alerta (cuantiles p99/p95 sobre snapshot servido)",
        "validation_strategy": (
            "Spatial StratifiedGroupKFold 5-fold OOF (bloques 50 km) + Validación Temporal Estricta (2024–2025 -> 2026)"
            if temporal_metrics
            else "Spatial StratifiedGroupKFold 5-fold out-of-fold (bloques de 50 km sin fuga espacial)"
        ),
        "random_baseline_precision": round(float(y.mean()), 5),
        "operating_threshold": optimal_thresh,
        "alert_budget": alert_budget,
        "serving_thresholds": serving_thresholds,
        "oof_thresholds": oof_thresholds,
        "score_quantiles": score_quantiles,
        "metrics": {
            "baseline": {
                "f1_score": round(float(base_f1), 4),
                "recall": round(float(base_rec), 4),
                "roc_auc": round(float(base_auc), 4),
                "average_precision": round(float(base_ap), 4),
            },
            "optimized_ensemble": {
                "f1_score": round(float(final_f1), 4),
                "precision": round(float(final_prec), 4),
                "recall": round(float(final_rec), 4),
                "roc_auc": round(float(final_auc), 4),
                "roc_auc_fold_std": round(float(np.std(fold_aucs)), 4) if fold_aucs else None,
                "average_precision": round(float(final_ap), 4),
                "average_precision_fold_std": round(float(np.std(fold_ap)), 4) if fold_ap else None,
                "recall_at_top_1pct": round(float(np.mean(rec_opt[0.01])), 4),
                "recall_at_top_5pct": round(float(np.mean(rec_opt[0.05])), 4),
                "recall_at_top_10pct": round(float(np.mean(rec_opt[0.10])), 4),
                "recall_at_top_20pct": round(float(np.mean(rec_opt[0.20])), 4),
            },
            **({"temporal_validation": temporal_metrics} if temporal_metrics else {}),
        },
        "optuna_best_params": {k: (float(v) if isinstance(v, (int, float, np.floating)) else v) for k, v in lgb_params.items()},
        "optuna_xgb_params": {k: (float(v) if isinstance(v, (int, float, np.floating)) else v) for k, v in xgb_params.items()},
        "shap_feature_importance": shap_importance,
    }

    meta_path = out_model.parent / "model_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Modelo Ensemble {model_ver} guardado en: {out_model}")
    print(f"📄 Metadatos y registro MLOps guardados en: {meta_path}")


def main():
    parser = argparse.ArgumentParser(description="Entrena pipeline avanzado de ML v2.5.0 (Panel Multi-fecha + Spatial/Temporal CV + Optuna + SHAP)")
    parser.add_argument("--input", default="data/dataset.parquet", help="Ruta del dataset o panel multi-fecha")
    parser.add_argument("--serve-dataset", default=None, help="Snapshot servido por la API (para cuantiles del semáforo)")
    parser.add_argument("--out", default="models/lightgbm_wildfire.pkl", help="Ruta de salida del modelo")
    parser.add_argument("--trials", type=int, default=20, help="Número de trials para Optuna (LightGBM)")
    args = parser.parse_args()

    train_advanced_pipeline(
        args.input,
        args.out,
        optuna_trials=args.trials,
        serve_dataset_path=args.serve_dataset,
    )


if __name__ == "__main__":
    main()
