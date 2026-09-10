"""
Entrena el modelo LightGBM para clasificación de riesgo de incendios forestales en grillas de 1km².
Maneja el desbalance de clases y evalúa métricas (F1-score, Recall, ROC-AUC).

Uso:
    python data_pipeline/train_model.py --input data/dataset.parquet --out models/lightgbm_wildfire.pkl
"""
import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, f1_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

FEATURE_COLUMNS = [
    "pendiente_pct", "ndvi", "dist_carretera_m", "dist_poblado_m",
    "temp_2m", "humedad_relativa", "viento_velocidad", "viento_direccion",
]


def train_wildfire_model(data_path: str, model_output_path: str):
    print(f"📊 Cargando dataset desde {data_path}...")
    if data_path.endswith(".parquet"):
        df = pd.read_parquet(data_path)
    else:
        df = pd.read_csv(data_path)

    # Eliminar columna de geometría si existe
    if "geometry" in df.columns:
        df = df.drop(columns=["geometry"])

    X = df[FEATURE_COLUMNS]
    y = df["target"]

    print(f"  -> Total muestras: {len(df)}")
    print(f"  -> Positivos (Target=1): {y.sum()} ({y.mean():.4%})")
    print(f"  -> Negativos (Target=0): {(y == 0).sum()}")

    # Split train/test estratificado por target
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Configurar LightGBM con manejo de desbalance
    scale_pos_weight = max(1.0, (len(y_train) - y_train.sum()) / max(1, y_train.sum()))
    print(f"⚖️ Factor de peso de clase (scale_pos_weight): {scale_pos_weight:.2f}")

    clf = lgb.LGBMClassifier(
        n_estimators=150,
        learning_rate=0.05,
        max_depth=6,
        num_leaves=31,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        verbosity=-1,
    )

    print("🤖 Entrenando modelo LightGBM...")
    clf.fit(X_train, y_train)

    # Evaluaciones
    y_pred_proba = clf.predict_proba(X_test)[:, 1]
    y_pred = (y_pred_proba >= 0.5).astype(int)

    f1 = f1_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    try:
        auc = roc_auc_score(y_test, y_pred_proba)
    except Exception:
        auc = 0.0

    print("\n--- 📈 RESULTADOS DE EVALUACIÓN ---")
    print(f"🎯 F1-Score: {f1:.4f}")
    print(f"🔍 Detección/Recall (Target=1): {recall:.4%} (Meta Capstone: >= 80%)")
    print(f"📐 ROC-AUC: {auc:.4f}")
    print("\nReportación detallada:")
    print(classification_report(y_test, y_pred, zero_division=0))

    # Guardar modelo
    out_file = Path(model_output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, out_file)
    print(f"✅ Modelo guardado exitosamente en: {out_file}")


def main():
    parser = argparse.ArgumentParser(description="Entrena modelo LightGBM para predicción de incendios")
    parser.add_argument("--input", default="data/dataset.parquet")
    parser.add_argument("--out", default="models/lightgbm_wildfire.pkl")
    args = parser.parse_args()

    train_wildfire_model(args.input, args.out)


if __name__ == "__main__":
    main()
