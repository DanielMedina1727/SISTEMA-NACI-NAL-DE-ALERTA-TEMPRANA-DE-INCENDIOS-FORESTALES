"""
Evaluación comparativa del modelo para el informe Capstone (Entregable Semana 8).
Compara LightGBM contra Random Forest y Regresión Logística sobre el dataset REAL
(etiqueta = focos de calor NASA FIRMS; features de Copernicus DEM, Sentinel-2 NDVI,
ERA5/Open-Meteo y OpenStreetMap).

Metodología: validación ESPACIAL 5-fold out-of-fold (GroupKFold por bloques de 50 km),
la misma que usa el pipeline de producción (data_pipeline/train_model.py). Se reporta
ROC-AUC (principal, libre de umbral) y Recall@Top-10% (presupuesto de alerta) porque con
~45 positivos reales las probabilidades absolutas son bajas y un umbral fijo de 0.5 no
es un criterio válido.

Uso:
    python notebooks/model_evaluation.py
"""
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

DATA_PATH = Path(__file__).parent.parent / "data" / "dataset.csv"

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Fuente única de verdad de las 18 features (evita listas desactualizadas de 8 columnas)
from app.model import FEATURE_ORDER as FEATURE_COLS


def _spatial_blocks(df: pd.DataFrame) -> pd.Series:
    """Bloques espaciales (~50 km) para GroupKFold, sin fuga entre train y test."""
    if "spatial_block_id" in df.columns:
        return df["spatial_block_id"]
    lat_b = ((df["latitude"] - df["latitude"].min()) // 0.45).astype(int)
    lon_b = ((df["longitude"] - df["longitude"].min()) // 0.45).astype(int)
    return pd.Series([f"block_{a}_{b}" for a, b in zip(lat_b, lon_b)], index=df.index)


def _recall_at_top(y_true: np.ndarray, probas: np.ndarray, budget: float = 0.10) -> float:
    """Fracción de incendios capturada en el `budget` de celdas de mayor riesgo."""
    k = max(1, int(len(probas) * budget))
    top = np.argsort(probas)[::-1][:k]
    return float(np.asarray(y_true)[top].sum()) / max(1, int(np.asarray(y_true).sum()))


def evaluate_models():
    print("📊 Cargando dataset para evaluación comparativa Capstone...")
    if not DATA_PATH.exists():
        print("⚠️ Dataset no encontrado en data/dataset.csv")
        return

    df = pd.read_csv(DATA_PATH)
    X = df[FEATURE_COLS]
    y = df["target"].to_numpy()
    groups = _spatial_blocks(df).to_numpy()

    scale_pos_weight = max(1.0, (len(y) - y.sum()) / max(1, y.sum()))
    models = {
        "LightGBM (Propuesto)": lambda: lgb.LGBMClassifier(
            n_estimators=400, learning_rate=0.04, num_leaves=15, max_depth=5,
            min_child_samples=80, colsample_bytree=0.8, subsample=0.8,
            scale_pos_weight=min(20.0, scale_pos_weight), random_state=42, verbosity=-1),
        "Random Forest": lambda: RandomForestClassifier(
            class_weight="balanced", random_state=42, n_estimators=200),
        "Regresión Logística": lambda: LogisticRegression(
            class_weight="balanced", max_iter=1000, random_state=42),
    }

    print("\n--- ⚔️ TABLA COMPARATIVA DE MODELOS (VALIDACIÓN ESPACIAL 5-FOLD OOF) ---")
    gkf = GroupKFold(n_splits=5)
    results = []
    for name, factory in models.items():
        aucs, rec10 = [], []
        for tr, te in gkf.split(X, y, groups):
            model = factory().fit(X.iloc[tr], y[tr])
            proba = model.predict_proba(X.iloc[te])[:, 1]
            if len(np.unique(y[te])) > 1:
                aucs.append(roc_auc_score(y[te], proba))
            rec10.append(_recall_at_top(y[te], proba, 0.10))
        mean_auc = float(np.mean(aucs)) if aucs else float("nan")
        results.append({
            "Modelo": name,
            "ROC-AUC (media±std)": f"{mean_auc:.3f} ± {np.std(aucs):.3f}",
            "Recall@Top-10%": f"{np.mean(rec10):.2%}",
            "_auc": mean_auc,
        })

    print(pd.DataFrame(results).drop(columns=["_auc"]).to_string(index=False))

    print("\n💡 CONCLUSIÓN CAPSTONE:")
    best = max(results, key=lambda r: r["_auc"])
    print(f"El mejor ROC-AUC en validación espacial fue '{best['Modelo']}' ({best['ROC-AUC (media±std)']}).")
    print("Los modelos de árboles (LightGBM / Ensemble) se eligen por su interpretabilidad (SHAP),")
    print("su bajo tiempo de inferencia (<2 ms) y su buen desempeño en datos tabulares.")
    print("Nota: con ~45 positivos reales y validación espacial estricta, un ROC-AUC de ~0.6-0.7")
    print("es lo esperable; alcanzar Recall >= 80% exige más eventos de incendio o features de mayor resolución.")


if __name__ == "__main__":
    evaluate_models()
