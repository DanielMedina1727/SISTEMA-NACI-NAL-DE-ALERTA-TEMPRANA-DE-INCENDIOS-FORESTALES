"""
test_lightgbm_precision.py
==========================
Pruebas exhaustivas de precisión del modelo LightGBM para detectar
"puntos de claro" (clearings) — zonas de alto riesgo de ignición.

Ejecutar:
    python tests/test_lightgbm_precision.py

Genera un reporte de consola con métricas por escenario y un resumen final.
"""

import sys
import time
from pathlib import Path

# Asegurar que el raíz del proyecto esté en el path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Forzar UTF-8 en la salida estándar (necesario en Windows con cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import joblib
import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# Cargar modelo
# ─────────────────────────────────────────────────────────────────────────────
MODEL_PATH = ROOT / "models" / "lightgbm_wildfire.pkl"

def load_model():
    if not MODEL_PATH.exists():
        print(f"[ERROR] Modelo no encontrado en: {MODEL_PATH}")
        print("        Ejecuta: python data_pipeline/train_model.py")
        sys.exit(1)
    return joblib.load(MODEL_PATH)

FEATURE_ORDER = [
    "pendiente_pct", "ndvi", "dist_carretera_m", "dist_poblado_m",
    "temp_2m", "humedad_relativa", "viento_velocidad", "viento_direccion",
]

UMBRAL_ROJO     = 0.70  # >= Rojo
UMBRAL_AMARILLO = 0.35  # >= Amarillo

def clasificar(p: float) -> str:
    if p >= UMBRAL_ROJO:
        return "🔴 Rojo"
    elif p >= UMBRAL_AMARILLO:
        return "🟡 Amarillo"
    return "🟢 Verde"


# ─────────────────────────────────────────────────────────────────────────────
# BANCO DE PRUEBAS — Puntos de Claro / Escenarios de Riesgo
# ─────────────────────────────────────────────────────────────────────────────
# Formato: (nombre, features_dict, nivel_esperado)
# "nivel_esperado" puede ser "Rojo", "Amarillo" o "Verde"

TEST_CASES = [
    # ── ESCENARIOS CRÍTICOS (nivel esperado: ROJO) ─────────────────────────
    (
        "Punto Claro #1 — Caserío El Mirador (alta pendiente + sequía)",
        {
            "pendiente_pct": 38.0,  # ladera empinada
            "ndvi": 0.12,           # vegetación muy seca
            "dist_carretera_m": 120.0,
            "dist_poblado_m": 350.0,
            "temp_2m": 34.5,
            "humedad_relativa": 18.0,
            "viento_velocidad": 32.0,
            "viento_direccion": 45.0,
        },
        "Rojo",
    ),
    (
        "Punto Claro #2 — Cerro Quilish (viento fuerte NE + NDVI bajo)",
        {
            "pendiente_pct": 28.0,
            "ndvi": 0.09,
            "dist_carretera_m": 800.0,
            "dist_poblado_m": 2000.0,
            "temp_2m": 31.0,
            "humedad_relativa": 15.0,
            "viento_velocidad": 45.0,
            "viento_direccion": 50.0,
        },
        "Rojo",
    ),
    (
        "Punto Claro #3 — Zona Pampa Grande (calor extremo + sin humedad)",
        {
            "pendiente_pct": 22.0,
            "ndvi": 0.18,
            "dist_carretera_m": 250.0,
            "dist_poblado_m": 500.0,
            "temp_2m": 36.8,
            "humedad_relativa": 12.0,
            "viento_velocidad": 28.0,
            "viento_direccion": 30.0,
        },
        "Rojo",
    ),
    (
        "Punto Claro #4 — Ladera Contumaza (ruta agrícola + pendiente alta)",
        {
            "pendiente_pct": 42.0,
            "ndvi": 0.14,
            "dist_carretera_m": 60.0,   # muy cerca de carretera (ignición humana)
            "dist_poblado_m": 180.0,
            "temp_2m": 33.0,
            "humedad_relativa": 20.0,
            "viento_velocidad": 25.0,
            "viento_direccion": 135.0,
        },
        "Rojo",
    ),
    (
        "Punto Claro #5 — Jalca Grande (altiplano seco + racha severa)",
        {
            "pendiente_pct": 18.0,
            "ndvi": 0.10,
            "dist_carretera_m": 1500.0,
            "dist_poblado_m": 4000.0,
            "temp_2m": 29.0,
            "humedad_relativa": 10.0,
            "viento_velocidad": 55.0,   # viento muy fuerte
            "viento_direccion": 270.0,
        },
        "Rojo",
    ),
    (
        "Punto Claro #6 — Cajabamba (bordes quema agrícola + baja humedad)",
        {
            "pendiente_pct": 25.0,
            "ndvi": 0.16,
            "dist_carretera_m": 90.0,
            "dist_poblado_m": 240.0,
            "temp_2m": 35.0,
            "humedad_relativa": 14.0,
            "viento_velocidad": 30.0,
            "viento_direccion": 60.0,
        },
        "Rojo",
    ),

    # ── ESCENARIOS DE VIGILANCIA (nivel esperado: AMARILLO) ────────────────
    (
        "Vigilancia #1 — Granja Porcón (NDVI medio, viento moderado)",
        {
            "pendiente_pct": 14.0,
            "ndvi": 0.38,
            "dist_carretera_m": 600.0,
            "dist_poblado_m": 1200.0,
            "temp_2m": 26.5,
            "humedad_relativa": 38.0,
            "viento_velocidad": 18.0,
            "viento_direccion": 45.0,
        },
        "Amarillo",
    ),
    (
        "Vigilancia #2 — Llanogrande (condiciones moderadas, pastizales)",
        {
            "pendiente_pct": 10.0,
            "ndvi": 0.30,
            "dist_carretera_m": 400.0,
            "dist_poblado_m": 900.0,
            "temp_2m": 28.0,
            "humedad_relativa": 32.0,
            "viento_velocidad": 15.0,
            "viento_direccion": 90.0,
        },
        "Amarillo",
    ),
    (
        "Vigilancia #3 — Baños del Inca (cercanía urbana, pendiente suave)",
        {
            "pendiente_pct": 8.0,
            "ndvi": 0.42,
            "dist_carretera_m": 200.0,
            "dist_poblado_m": 300.0,
            "temp_2m": 27.0,
            "humedad_relativa": 40.0,
            "viento_velocidad": 12.0,
            "viento_direccion": 180.0,
        },
        "Amarillo",
    ),

    # ── ESCENARIOS SEGUROS (nivel esperado: VERDE) ─────────────────────────
    (
        "Zona Segura #1 — Bosque Huambos (alta cobertura vegetal + lluvia reciente)",
        {
            "pendiente_pct": 5.0,
            "ndvi": 0.78,
            "dist_carretera_m": 3000.0,
            "dist_poblado_m": 5000.0,
            "temp_2m": 18.0,
            "humedad_relativa": 82.0,
            "viento_velocidad": 5.0,
            "viento_direccion": 180.0,
        },
        "Verde",
    ),
    (
        "Zona Segura #2 — Laguna San Nicolás (zona húmeda, sin pendiente)",
        {
            "pendiente_pct": 2.0,
            "ndvi": 0.85,
            "dist_carretera_m": 8000.0,
            "dist_poblado_m": 10000.0,
            "temp_2m": 14.0,
            "humedad_relativa": 92.0,
            "viento_velocidad": 3.0,
            "viento_direccion": 270.0,
        },
        "Verde",
    ),
    (
        "Zona Segura #3 — Fundo Santa Teresa (irrigado, temperatura suave)",
        {
            "pendiente_pct": 4.0,
            "ndvi": 0.65,
            "dist_carretera_m": 1200.0,
            "dist_poblado_m": 2500.0,
            "temp_2m": 20.0,
            "humedad_relativa": 70.0,
            "viento_velocidad": 8.0,
            "viento_direccion": 90.0,
        },
        "Verde",
    ),

    # ── CASOS LÍMITE / FRONTERA DE UMBRAL ─────────────────────────────────
    (
        "Frontera R/A — Condiciones justo en umbral Rojo (0.70)",
        {
            "pendiente_pct": 20.0,
            "ndvi": 0.25,
            "dist_carretera_m": 300.0,
            "dist_poblado_m": 700.0,
            "temp_2m": 30.0,
            "humedad_relativa": 25.0,
            "viento_velocidad": 22.0,
            "viento_direccion": 45.0,
        },
        None,  # Sin expectativa fija — medimos probabilidad exacta
    ),
    (
        "Frontera A/V — Condiciones cerca umbral Amarillo (0.35)",
        {
            "pendiente_pct": 10.0,
            "ndvi": 0.50,
            "dist_carretera_m": 1000.0,
            "dist_poblado_m": 2000.0,
            "temp_2m": 24.0,
            "humedad_relativa": 50.0,
            "viento_velocidad": 10.0,
            "viento_direccion": 180.0,
        },
        None,  # Sin expectativa fija
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Prueba de sensibilidad por variable (análisis de sensibilidad)
# ─────────────────────────────────────────────────────────────────────────────
BASE_FEATURES = {
    "pendiente_pct": 20.0,
    "ndvi": 0.30,
    "dist_carretera_m": 400.0,
    "dist_poblado_m": 800.0,
    "temp_2m": 28.0,
    "humedad_relativa": 32.0,
    "viento_velocidad": 20.0,
    "viento_direccion": 45.0,
}

SENSITIVITY_TESTS = {
    "pendiente_pct":      [2, 10, 20, 35, 50],
    "ndvi":               [0.05, 0.15, 0.35, 0.55, 0.75],
    "temp_2m":            [15, 20, 26, 30, 36],
    "humedad_relativa":   [10, 20, 35, 55, 80],
    "viento_velocidad":   [3, 10, 20, 35, 55],
    "dist_carretera_m":   [50, 200, 500, 1500, 5000],
}


def predict_one(model, features: dict) -> tuple[float, float]:
    """Devuelve (probabilidad, tiempo_ms)."""
    df = pd.DataFrame([{k: float(features.get(k, 0.0)) for k in FEATURE_ORDER}])
    t0 = time.perf_counter()
    proba = float(model.predict_proba(df)[0][1])
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return proba, elapsed_ms


def separator(char="─", n=80):
    print(char * n)


def run_all_tests():
    print("\n" + "=" * 80)
    print("  🔥 PRUEBAS DE PRECISIÓN — LightGBM | Sistema de Alerta Temprana de Incendios")
    print("=" * 80)

    model = load_model()
    print(f"\n✅ Modelo cargado desde: {MODEL_PATH}")
    print(f"   Tipo: {type(model).__name__}")
    separator()

    # ── 1. CASOS DE PRUEBA ESTÁTICOS ──────────────────────────────────────
    print("\n📋 SECCIÓN 1 — CASOS DE PRUEBA ESTÁTICOS (puntos de claro y zonas seguras)")
    separator()

    results = []
    total_infer_ms = []

    for nombre, feats, esperado in TEST_CASES:
        proba, ms = predict_one(model, feats)
        nivel = clasificar(proba)
        total_infer_ms.append(ms)

        correcto = None
        if esperado is not None:
            correcto = nivel.split()[-1] == esperado  # compara sin emoji
            status = "✅ OK" if correcto else "❌ FALLA"
        else:
            status = "📏 Frontera"

        results.append({
            "Nombre": nombre[:60],
            "Probabilidad": proba,
            "Nivel": nivel,
            "Esperado": esperado or "—",
            "Resultado": status,
            "ms": ms,
        })

        print(f"\n  {status}  {nombre}")
        print(f"       Probabilidad : {proba:.4f} ({proba:.1%})")
        print(f"       Clasificación: {nivel}  |  Esperado: {esperado or '—'}")
        print(f"       Inferencia   : {ms:.3f} ms")

    # Resumen sección 1
    separator()
    total_casos = sum(1 for r in results if r["Esperado"] != "—")
    aciertos = sum(1 for r in results if "✅" in r["Resultado"])
    pct = (aciertos / total_casos * 100) if total_casos > 0 else 0

    print(f"\n  📊 Precisión sección 1 : {aciertos}/{total_casos} ({pct:.1f}%)")
    print(f"  ⚡ Latencia promedio  : {np.mean(total_infer_ms):.3f} ms")
    print(f"  ⚡ Latencia máxima    : {np.max(total_infer_ms):.3f} ms")

    # ── 2. ANÁLISIS DE SENSIBILIDAD ───────────────────────────────────────
    print("\n\n📋 SECCIÓN 2 — ANÁLISIS DE SENSIBILIDAD (impacto de cada variable)")
    separator()

    for var, valores in SENSITIVITY_TESTS.items():
        row_vals = []
        for v in valores:
            feats = {**BASE_FEATURES, var: v}
            p, _ = predict_one(model, feats)
            row_vals.append(p)

        print(f"\n  Variable: {var}")
        print(f"  {'Valor':>10}  {'P(incendio)':>13}  {'Nivel':>12}")
        print("  " + "-" * 40)
        for v, p in zip(valores, row_vals):
            niv = clasificar(p)
            bar = "█" * int(p * 20)
            print(f"  {v:>10}  {p:>10.4f} ({p:>5.1%})  {niv}  {bar}")

    # ── 3. PRUEBA DE ESTRÉS — INFERENCIA EN LOTE ─────────────────────────
    print("\n\n📋 SECCIÓN 3 — PRUEBA DE ESTRÉS (inferencia en lote de 1,000 puntos)")
    separator()

    np.random.seed(42)
    N = 1000
    df_batch = pd.DataFrame({
        "pendiente_pct":    np.random.uniform(0, 60, N),
        "ndvi":             np.random.uniform(0.05, 0.90, N),
        "dist_carretera_m": np.random.uniform(50, 10000, N),
        "dist_poblado_m":   np.random.uniform(100, 15000, N),
        "temp_2m":          np.random.uniform(12, 40, N),
        "humedad_relativa": np.random.uniform(8, 95, N),
        "viento_velocidad": np.random.uniform(0, 70, N),
        "viento_direccion": np.random.uniform(0, 360, N),
    })

    t0 = time.perf_counter()
    probas_batch = model.predict_proba(df_batch[FEATURE_ORDER])[:, 1]
    elapsed_batch = (time.perf_counter() - t0) * 1000

    rojas    = int((probas_batch >= UMBRAL_ROJO).sum())
    amarillas = int(((probas_batch >= UMBRAL_AMARILLO) & (probas_batch < UMBRAL_ROJO)).sum())
    verdes   = int((probas_batch < UMBRAL_AMARILLO).sum())

    print(f"\n  N de muestras    : {N:,}")
    print(f"  Tiempo total     : {elapsed_batch:.2f} ms")
    print(f"  Tiempo por muestra: {elapsed_batch/N:.4f} ms")
    print(f"\n  Distribución de niveles:")
    print(f"    🔴 Rojo     : {rojas:>5} ({rojas/N:.1%})")
    print(f"    🟡 Amarillo : {amarillas:>5} ({amarillas/N:.1%})")
    print(f"    🟢 Verde    : {verdes:>5} ({verdes/N:.1%})")
    print(f"\n  Estadísticas P(incendio):")
    print(f"    Media   : {probas_batch.mean():.4f}")
    print(f"    Mediana : {np.median(probas_batch):.4f}")
    print(f"    Std     : {probas_batch.std():.4f}")
    print(f"    Mín     : {probas_batch.min():.4f}")
    print(f"    Máx     : {probas_batch.max():.4f}")

    # ── 4. PRUEBA DE CONSISTENCIA MONOTÓNICA ─────────────────────────────
    print("\n\n📋 SECCIÓN 4 — CONSISTENCIA MONOTÓNICA (incremento de riesgo)")
    separator()

    monotonic_tests = [
        ("Temperatura creciente →  P(riesgo) debe crecer",     "temp_2m",          [15, 20, 26, 32, 38], True),
        ("Humedad creciente    →  P(riesgo) debe BAJAR",        "humedad_relativa",  [10, 25, 45, 65, 85], False),
        ("NDVI creciente       →  P(riesgo) debe BAJAR",        "ndvi",             [0.05, 0.20, 0.40, 0.60, 0.80], False),
        ("Viento creciente     →  P(riesgo) debe crecer",       "viento_velocidad",  [2, 10, 20, 35, 60], True),
        ("Pendiente creciente  →  P(riesgo) debe crecer",       "pendiente_pct",     [2, 10, 20, 35, 50], True),
    ]

    monotonic_ok = 0
    for desc, var, vals, should_increase in monotonic_tests:
        ps = []
        for v in vals:
            f = {**BASE_FEATURES, var: v}
            p, _ = predict_one(model, f)
            ps.append(p)

        diffs = [ps[i+1] - ps[i] for i in range(len(ps)-1)]
        if should_increase:
            ok = all(d >= -0.05 for d in diffs)  # tolerancia ±5%
            trend_str = "↗ creciente"
        else:
            ok = all(d <= 0.05 for d in diffs)
            trend_str = "↘ decreciente"

        status = "✅" if ok else "⚠️ "
        if ok:
            monotonic_ok += 1
        vals_str = " → ".join(f"{p:.3f}" for p in ps)
        print(f"\n  {status} {desc}")
        print(f"     Tendencia esperada: {trend_str}")
        print(f"     P(incendio): {vals_str}")

    separator()
    print(f"\n  📊 Consistencia monotónica: {monotonic_ok}/{len(monotonic_tests)} pruebas superadas")

    # ── RESUMEN FINAL ─────────────────────────────────────────────────────
    print("\n\n" + "=" * 80)
    print("  📊 RESUMEN FINAL DE PRECISIÓN DEL MODELO LIGHTGBM")
    print("=" * 80)
    print(f"\n  Sección 1 — Casos estáticos de puntos de claro:")
    print(f"    • Precisión en clasificación : {aciertos}/{total_casos} ({pct:.1f}%)")
    print(f"    • Latencia media de inferencia: {np.mean(total_infer_ms):.3f} ms")
    print(f"\n  Sección 2 — Sensibilidad por variable:")
    print(f"    • Variables evaluadas : {len(SENSITIVITY_TESTS)}")
    print(f"    • Comportamiento      : ver detalle arriba")
    print(f"\n  Sección 3 — Inferencia en lote (N={N}):")
    print(f"    • Tiempo total        : {elapsed_batch:.2f} ms")
    print(f"    • Tiempo por muestra  : {elapsed_batch/N:.4f} ms (objetivo: < 2 ms)")
    latencia_ok = (elapsed_batch / N) < 2.0
    print(f"    • Objetivo < 2 ms     : {'✅ Cumplido' if latencia_ok else '❌ No cumplido'}")
    print(f"\n  Sección 4 — Consistencia monotónica:")
    print(f"    • Pruebas superadas   : {monotonic_ok}/{len(monotonic_tests)}")
    mono_ok = monotonic_ok == len(monotonic_tests)
    print(f"    • Estado              : {'✅ Completamente consistente' if mono_ok else '⚠️  Revisar tendencias'}")

    overall = pct >= 80 and latencia_ok and monotonic_ok >= len(monotonic_tests) - 1
    print(f"\n  {'✅ MODELO APROBADO' if overall else '⚠️  MODELO REQUIERE REVISIÓN'}")
    print("=" * 80 + "\n")

    return overall


if __name__ == "__main__":
    run_all_tests()
