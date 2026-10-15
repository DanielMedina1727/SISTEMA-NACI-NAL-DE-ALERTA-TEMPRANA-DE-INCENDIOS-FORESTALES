"""
iso25010_audit.py
=================
Auditoría completa del sistema AlertaForestal Perú según la norma ISO/IEC 25010:2011
(Calidad del Producto de Software).

Características evaluadas:
  1. Adecuación Funcional  (Functional Suitability)
  2. Eficiencia de Desempeño (Performance Efficiency)
  3. Compatibilidad         (Compatibility)
  4. Usabilidad             (Usability)
  5. Fiabilidad             (Reliability)
  6. Seguridad              (Security)
  7. Mantenibilidad         (Maintainability)
  8. Portabilidad           (Portability)

Ejecutar:
    python tests/iso25010_audit.py

Requiere: API corriendo en http://127.0.0.1:5050
"""

import sys
import time
import json
import math
import hashlib
import os
import re
import inspect
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import requests
import joblib
import numpy as np
import pandas as pd

BASE_URL = "http://127.0.0.1:5050"
MODEL_PATH = ROOT / "models" / "lightgbm_wildfire.pkl"
WEB_DIR = ROOT / "web"
APP_DIR = ROOT / "app"

# ─── Utilidades ──────────────────────────────────────────────────────────────

PASS = "✅ PASA"
FAIL = "❌ FALLA"
WARN = "⚠️  AVISO"
INFO = "ℹ️  INFO"

score_board = {}  # caracteristica -> [passed, total]

def register(caracteristica, passed: bool):
    if caracteristica not in score_board:
        score_board[caracteristica] = [0, 0]
    score_board[caracteristica][1] += 1
    if passed:
        score_board[caracteristica][0] += 1

def sep(char="─", n=80):
    print(char * n)

def header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def subheader(title):
    print(f"\n  ── {title}")

def result(label, passed, detail="", cat=None):
    icon = PASS if passed else FAIL
    print(f"  {icon}  {label}")
    if detail:
        print(f"         {detail}")
    if cat:
        register(cat, passed)
    return passed

def api_get(path, timeout=10, **params):
    try:
        r = requests.get(f"{BASE_URL}{path}", params=params, timeout=timeout)
        return r
    except requests.exceptions.ConnectionError:
        return None
    except Exception:
        return None

def api_post(path, payload, timeout=10):
    try:
        r = requests.post(f"{BASE_URL}{path}", json=payload, timeout=timeout)
        return r
    except requests.exceptions.ConnectionError:
        return None
    except Exception:
        return None

# ─────────────────────────────────────────────────────────────────────────────
# 1. ADECUACIÓN FUNCIONAL
# ─────────────────────────────────────────────────────────────────────────────

def test_functional_suitability():
    header("1. ADECUACIÓN FUNCIONAL (Functional Suitability) — ISO 25010 §4.1")
    CAT = "Adecuación Funcional"

    # 1.1 Completitud funcional — todos los endpoints deben existir
    subheader("1.1 Completitud funcional — endpoints requeridos")
    endpoints = [
        ("/health",           "GET",  None),
        ("/risk/today",       "GET",  None),
        ("/predict",          "POST", {
            "grid_id": "TEST-001", "pendiente_pct": 25.0, "orientacion": "NE",
            "ndvi": 0.20, "dist_carretera_m": 200.0, "dist_poblado_m": 500.0,
            "temp_2m": 32.0, "humedad_relativa": 18.0,
            "viento_velocidad": 30.0, "viento_direccion": 45.0
        }),
        ("/firms/hotspots",   "GET",  None),
        ("/model/importance", "GET",  None),
        ("/social/matrix",    "GET",  None),
        ("/report/pdf",       "GET",  None),
        ("/alert/status",     "GET",  None),
    ]

    for path, method, body in endpoints:
        if method == "GET":
            r = api_get(path)
        else:
            r = api_post(path, body)

        if r is None:
            ok = False
            detail = "API no disponible"
        else:
            ok = r.status_code < 500
            detail = f"HTTP {r.status_code}"
        result(f"Endpoint {method} {path}", ok, detail, CAT)

    # 1.2 Corrección funcional — /predict retorna estructura correcta
    subheader("1.2 Corrección funcional — /predict responde con estructura válida")
    payload = {
        "grid_id": "CAJ-ISO-001",
        "pendiente_pct": 38.0, "orientacion": "NE",
        "ndvi": 0.12, "dist_carretera_m": 120.0, "dist_poblado_m": 350.0,
        "temp_2m": 34.5, "humedad_relativa": 18.0,
        "viento_velocidad": 32.0, "viento_direccion": 45.0
    }
    r = api_post("/predict", payload)
    if r and r.status_code == 200:
        data = r.json()
        has_fields = all(k in data for k in ["grid_id", "probabilidad", "nivel"])
        result("Respuesta contiene grid_id, probabilidad, nivel", has_fields, str(data), CAT)
        proba_valid = 0.0 <= data.get("probabilidad", -1) <= 1.0
        result("probabilidad en rango [0,1]", proba_valid, f"p={data.get('probabilidad')}", CAT)
        nivel_valid = data.get("nivel") in ["Verde", "Amarillo", "Rojo"]
        result("nivel es Verde/Amarillo/Rojo", nivel_valid, f"nivel={data.get('nivel')}", CAT)
        # La clasificación debe ser consistente con los umbrales operativos del modelo
        from app.model import classify as _clf
        consistente = data.get("nivel") == _clf(data.get("probabilidad", 0.0))
        result("Clasificación consistente con los umbrales del modelo", consistente,
               f"nivel={data.get('nivel')} p={data.get('probabilidad',0):.4f} "
               f"percentil={data.get('percentil')}", CAT)
    else:
        code = r.status_code if r else "sin respuesta"
        for lbl in ["Respuesta contiene grid_id, probabilidad, nivel",
                    "probabilidad en rango [0,1]", "nivel es Verde/Amarillo/Rojo",
                    "Clasificación consistente con los umbrales del modelo"]:
            result(lbl, False, f"HTTP {code}", CAT)

    # 1.3 Corrección funcional — /risk/today retorna GeoJSON válido
    subheader("1.3 Corrección funcional — /risk/today retorna GeoJSON válido")
    r = api_get("/risk/today", limit=10)
    if r and r.status_code == 200:
        data = r.json()
        is_geojson = data.get("type") == "FeatureCollection"
        result("Tipo FeatureCollection", is_geojson, "", CAT)
        has_features = "features" in data and isinstance(data["features"], list)
        result("Campo 'features' es lista", has_features, f"count={data.get('count')}", CAT)
        if has_features and data["features"]:
            feat = data["features"][0]
            valid_geom = feat.get("geometry", {}).get("type") == "Polygon"
            result("Geometría es Polygon", valid_geom, "", CAT)
            props = feat.get("properties", {})
            has_nivel = "nivel" in props and "probabilidad" in props
            result("Propiedades nivel y probabilidad presentes", has_nivel, str(list(props.keys())), CAT)
    else:
        code = r.status_code if r else "sin respuesta"
        for lbl in ["Tipo FeatureCollection","Campo 'features' es lista",
                    "Geometría es Polygon","Propiedades nivel y probabilidad presentes"]:
            result(lbl, False, f"HTTP {code}", CAT)

    # 1.4 Apropiación funcional — /propagate genera grillas afectadas
    subheader("1.4 Apropiación funcional — motor de propagación")
    r = api_post("/propagate?grid_id=-78.5000_-7.1600&viento_direccion=45&viento_velocidad=25", {})
    if r and r.status_code == 200:
        data = r.json()
        has_grillas = "grillas_afectadas" in data and len(data["grillas_afectadas"]) > 0
        result("Propagación genera grillas afectadas", has_grillas,
               f"afectadas={len(data.get('grillas_afectadas', []))}", CAT)
        if has_grillas:
            g = data["grillas_afectadas"][0]
            has_prob = 0 < g.get("probabilidad_recibir_fuego", -1) <= 1
            result("Probabilidad de recepción en rango válido", has_prob,
                   f"p={g.get('probabilidad_recibir_fuego')}", CAT)
    else:
        code = r.status_code if r else "sin respuesta"
        result("Propagación genera grillas afectadas", False, f"HTTP {code}", CAT)
        result("Probabilidad de recepción en rango válido", False, f"HTTP {code}", CAT)

    # 1.5 /health reporta estado del modelo
    subheader("1.5 Completitud — /health reporta estado del sistema")
    r = api_get("/health")
    if r and r.status_code == 200:
        data = r.json()
        has_model_status = "model_loaded" in data
        result("Campo model_loaded presente", has_model_status, str(data), CAT)
        has_dataset_status = "dataset_available" in data
        result("Campo dataset_available presente", has_dataset_status, str(data), CAT)
    else:
        result("Campo model_loaded presente", False, "Sin respuesta", CAT)
        result("Campo dataset_available presente", False, "Sin respuesta", CAT)


# ─────────────────────────────────────────────────────────────────────────────
# 2. EFICIENCIA DE DESEMPEÑO
# ─────────────────────────────────────────────────────────────────────────────

def test_performance_efficiency():
    header("2. EFICIENCIA DE DESEMPEÑO (Performance Efficiency) — ISO 25010 §4.2")
    CAT = "Eficiencia de Desempeño"

    # 2.1 Comportamiento temporal — latencia de endpoints
    subheader("2.1 Comportamiento temporal — latencias de respuesta")

    targets = {
        "/health":           200,   # < 200 ms
        "/predict":          300,   # < 300 ms
        "/risk/today":      3000,   # < 3000 ms (dataset grande)
        "/model/importance": 500,   # < 500 ms
    }

    for path, max_ms in targets.items():
        times = []
        for _ in range(3):
            t0 = time.perf_counter()
            if path == "/predict":
                r = api_post(path, {
                    "grid_id": "PERF-001", "pendiente_pct": 20.0, "orientacion": "NE",
                    "ndvi": 0.30, "dist_carretera_m": 400.0, "dist_poblado_m": 800.0,
                    "temp_2m": 28.0, "humedad_relativa": 32.0,
                    "viento_velocidad": 20.0, "viento_direccion": 45.0
                })
            else:
                r = api_get(path, **{"limit": 50} if "risk" in path else {})
            elapsed = (time.perf_counter() - t0) * 1000
            if r and r.status_code < 500:
                times.append(elapsed)

        if times:
            avg_ms = sum(times) / len(times)
            ok = avg_ms < max_ms
            result(f"GET {path} latencia media < {max_ms} ms", ok,
                   f"media={avg_ms:.1f} ms (objetivo <{max_ms} ms)", CAT)
        else:
            result(f"GET {path} latencia media < {max_ms} ms", False, "Sin respuesta", CAT)

    # 2.2 Inferencia del modelo — < 2 ms por muestra (lote 1000)
    subheader("2.2 Inferencia ML — objetivo < 2 ms/muestra (lote 1000)")
    try:
        model = joblib.load(MODEL_PATH)
        from app.model import FEATURE_ORDER, DEFAULT_VALUES
        np.random.seed(42)
        N = 1000
        RANGOS = {
            "pendiente_pct": (0, 60), "ndvi": (0.05, 0.90),
            "dist_carretera_m": (50, 10000), "dist_poblado_m": (100, 15000),
            "temp_2m": (12, 40), "humedad_relativa": (8, 95),
            "viento_velocidad": (0, 70), "viento_direccion": (0, 360),
        }
        df = pd.DataFrame({
            col: (np.random.uniform(*RANGOS[col], N) if col in RANGOS else DEFAULT_VALUES.get(col, 0.0))
            for col in FEATURE_ORDER
        })
        t0 = time.perf_counter()
        _ = model.predict_proba(df[FEATURE_ORDER])[:, 1]
        elapsed_ms = (time.perf_counter() - t0) * 1000
        ms_per_sample = elapsed_ms / N
        ok = ms_per_sample < 2.0
        result(f"Inferencia en lote N={N}", ok,
               f"{ms_per_sample:.4f} ms/muestra (total {elapsed_ms:.1f} ms)", CAT)
    except Exception as e:
        result("Inferencia en lote N=1000", False, str(e), CAT)

    # 2.3 Capacidad de carga — múltiples peticiones sucesivas
    subheader("2.3 Capacidad — 20 peticiones consecutivas /health")
    times_health = []
    errors = 0
    for _ in range(20):
        t0 = time.perf_counter()
        r = api_get("/health")
        elapsed = (time.perf_counter() - t0) * 1000
        if r and r.status_code == 200:
            times_health.append(elapsed)
        else:
            errors += 1
    ok_rate = (len(times_health) / 20) >= 0.95
    result("Tasa de éxito ≥ 95% en 20 peticiones consecutivas", ok_rate,
           f"{len(times_health)}/20 exitosas, media={np.mean(times_health):.1f} ms", CAT)
    if times_health:
        ok_p95 = np.percentile(times_health, 95) < 500
        result("P95 de latencia /health < 500 ms", ok_p95,
               f"P95={np.percentile(times_health, 95):.1f} ms", CAT)


# ─────────────────────────────────────────────────────────────────────────────
# 3. COMPATIBILIDAD
# ─────────────────────────────────────────────────────────────────────────────

def test_compatibility():
    header("3. COMPATIBILIDAD (Compatibility) — ISO 25010 §4.3")
    CAT = "Compatibilidad"

    # 3.1 Cabeceras CORS
    subheader("3.1 Co-existencia — cabeceras CORS presentes")
    # El header CORS solo se emite cuando la peticion trae Origin (comportamiento real)
    try:
        r = requests.get(f"{BASE_URL}/health", headers={"Origin": "http://example.com"}, timeout=8)
    except Exception:
        r = None
    if r is not None:
        cors = r.headers.get("access-control-allow-origin", "")
        ok = cors == "*" or len(cors) > 0
        result("Access-Control-Allow-Origin presente", ok, f"valor='{cors}'", CAT)
    else:
        result("Access-Control-Allow-Origin presente", False, "Sin respuesta", CAT)

    # 3.2 Content-Type JSON
    subheader("3.2 Interoperabilidad — respuestas en JSON estándar")
    endpoints_json = ["/health", "/risk/today?limit=5", "/model/importance"]
    for ep in endpoints_json:
        r = api_get(ep)
        if r and r.status_code == 200:
            ct = r.headers.get("content-type", "")
            ok = "application/json" in ct
            result(f"Content-Type JSON en {ep}", ok, f"content-type='{ct}'", CAT)
        else:
            result(f"Content-Type JSON en {ep}", False, "Sin respuesta", CAT)

    # 3.3 PDF retorna content-type correcto
    subheader("3.3 Interoperabilidad — /report/pdf retorna PDF")
    r = api_get("/report/pdf", timeout=30)
    if r and r.status_code == 200:
        ct = r.headers.get("content-type", "")
        ok = "application/pdf" in ct
        result("/report/pdf Content-Type=application/pdf", ok, f"content-type='{ct}'", CAT)
        ok_size = len(r.content) > 1000
        result("/report/pdf tamaño > 1 KB", ok_size, f"tamaño={len(r.content)/1024:.1f} KB", CAT)
    else:
        code = r.status_code if r else "sin respuesta"
        result("/report/pdf Content-Type=application/pdf", False, f"HTTP {code}", CAT)
        result("/report/pdf tamaño > 1 KB", False, f"HTTP {code}", CAT)

    # 3.4 GeoJSON estándar compatible con Leaflet/QGIS
    subheader("3.4 Interoperabilidad — GeoJSON cumple estándar RFC 7946")
    r = api_get("/risk/today", limit=5)
    if r and r.status_code == 200:
        data = r.json()
        ok_type = data.get("type") == "FeatureCollection"
        result("type='FeatureCollection' (RFC 7946)", ok_type, "", CAT)
        feats = data.get("features", [])
        if feats:
            f0 = feats[0]
            ok_geom = f0.get("geometry", {}).get("type") in ["Point", "Polygon", "MultiPolygon"]
            result("Tipo de geometría válido (RFC 7946)", ok_geom,
                   f"type={f0.get('geometry',{}).get('type')}", CAT)
            coords = f0.get("geometry", {}).get("coordinates", [])
            ok_coords = len(coords) > 0
            result("Coordenadas presentes", ok_coords, "", CAT)
    else:
        for lbl in ["type='FeatureCollection' (RFC 7946)",
                    "Tipo de geometría válido (RFC 7946)", "Coordenadas presentes"]:
            result(lbl, False, "Sin respuesta", CAT)

    # 3.5 API version header
    subheader("3.5 Interoperabilidad — documentación OpenAPI disponible")
    r = api_get("/docs")
    ok = r is not None and r.status_code == 200
    result("Swagger UI /docs accesible", ok, f"HTTP {r.status_code if r else 'sin respuesta'}", CAT)
    r2 = api_get("/openapi.json")
    ok2 = r2 is not None and r2.status_code == 200
    result("OpenAPI JSON /openapi.json disponible", ok2, f"HTTP {r2.status_code if r2 else 'sin respuesta'}", CAT)


# ─────────────────────────────────────────────────────────────────────────────
# 4. USABILIDAD
# ─────────────────────────────────────────────────────────────────────────────

def test_usability():
    header("4. USABILIDAD (Usability) — ISO 25010 §4.4")
    CAT = "Usabilidad"

    # 4.1 Portal web accesible
    subheader("4.1 Reconocimiento de idoneidad — portal web accesible")
    r = api_get("/")
    if r and r.status_code == 200:
        result("Portal web responde HTTP 200", True, f"HTTP {r.status_code}", CAT)
        ct = r.headers.get("content-type", "")
        is_html = "text/html" in ct
        result("Respuesta es HTML", is_html, f"content-type='{ct}'", CAT)
        html = r.text
        has_title = "<title>" in html.lower()
        result("Página contiene <title>", has_title, "", CAT)
        has_h1 = "<h1" in html.lower()
        result("Página contiene <h1>", has_h1, "", CAT)
    else:
        for lbl in ["Portal web responde HTTP 200","Respuesta es HTML",
                    "Página contiene <title>","Página contiene <h1>"]:
            result(lbl, False, "Sin respuesta", CAT)

    # 4.2 Verificar elementos de UI clave en index.html
    subheader("4.2 Operabilidad — elementos clave de UI presentes en index.html")
    index_html = WEB_DIR / "index.html"
    if index_html.exists():
        html = index_html.read_text(encoding="utf-8")

        checks = [
            ("Sección de mapa (#mapa)", 'id="mapa"'),
            ("Sección WhatsApp (#whatsapp)", 'id="whatsapp"'),
            ("Sección de reporte (#reporte)", 'id="reporte"'),
            ("Sección de recursos (#recursos)", 'id="recursos"'),
            ("Sección transparencia (#transparencia)", 'id="transparencia"'),
            ("Navegación principal (nav)", "<nav"),
            ("Botón CTA de reporte", "Reportar"),
            ("Leaflet incluido", "leaflet"),
            ("Mapa de calor (heatmap)", "heatmap"),
            ("Filtro de región", 'id="regionFilter"'),
            ("Selector de WhatsApp por provincia", 'id="waZone"'),
            ("Formulario de reporte ciudadano", 'id="reportForm"'),
            ("Estadísticas en tiempo real", 'id="statFIRMS"'),
            ("Meta description SEO", 'name="description"'),
            ("Viewport responsive", 'name="viewport"'),
            ("Google Fonts Inter", "fonts.googleapis.com"),
        ]

        for label, pattern in checks:
            ok = pattern.lower() in html.lower()
            result(label, ok, f"buscando: '{pattern}'", CAT)
    else:
        result("index.html existe", False, str(index_html), CAT)

    # 4.3 Mensajes de error descriptivos en la API
    subheader("4.3 Protección ante errores — respuestas de error descriptivas")
    r = api_post("/predict", {})  # falta el campo requerido grid_id
    if r is not None:
        # FastAPI retorna 422 con detalles de validación
        ok_422 = r.status_code == 422
        result("Validación de entrada retorna 422 Unprocessable Entity", ok_422,
               f"HTTP {r.status_code}", CAT)
        if ok_422:
            body = r.json()
            has_detail = "detail" in body
            result("Respuesta 422 contiene campo 'detail'", has_detail, str(body)[:100], CAT)
    else:
        result("Validación de entrada retorna 422 Unprocessable Entity", False, "Sin respuesta", CAT)

    # 4.4 Swagger UI contiene descripción del sistema
    subheader("4.4 Aprendizaje — OpenAPI contiene descripción y ejemplos")
    r = api_get("/openapi.json")
    if r and r.status_code == 200:
        schema = r.json()
        title = schema.get("info", {}).get("title", "")
        ok_title = len(title) > 5
        result("OpenAPI tiene título descriptivo", ok_title, f"título='{title}'", CAT)
        desc = schema.get("info", {}).get("description", "")
        ok_desc = len(desc) > 20
        result("OpenAPI tiene descripción detallada", ok_desc, f"len={len(desc)} chars", CAT)
        version = schema.get("info", {}).get("version", "")
        ok_ver = len(version) > 0
        result("OpenAPI tiene versión", ok_ver, f"version='{version}'", CAT)
        paths = schema.get("paths", {})
        ok_paths = len(paths) >= 8
        result(f"OpenAPI documenta ≥8 endpoints (actual: {len(paths)})", ok_paths, "", CAT)
    else:
        for lbl in ["OpenAPI tiene título descriptivo","OpenAPI tiene descripción detallada",
                    "OpenAPI tiene versión","OpenAPI documenta ≥8 endpoints"]:
            result(lbl, False, "Sin respuesta", CAT)


# ─────────────────────────────────────────────────────────────────────────────
# 5. FIABILIDAD
# ─────────────────────────────────────────────────────────────────────────────

def test_reliability():
    header("5. FIABILIDAD (Reliability) — ISO 25010 §4.5")
    CAT = "Fiabilidad"

    # 5.1 Madurez — múltiples llamadas sin error
    subheader("5.1 Madurez — 10 llamadas repetidas a /predict sin errores")
    payload = {
        "grid_id": "REL-001", "pendiente_pct": 20.0, "orientacion": "NE",
        "ndvi": 0.30, "dist_carretera_m": 400.0, "dist_poblado_m": 800.0,
        "temp_2m": 28.0, "humedad_relativa": 32.0,
        "viento_velocidad": 20.0, "viento_direccion": 45.0
    }
    successes = 0
    results_probas = []
    for _ in range(10):
        r = api_post("/predict", payload)
        if r and r.status_code == 200:
            successes += 1
            results_probas.append(r.json().get("probabilidad", -1))
    ok_all = successes == 10
    result("10/10 llamadas a /predict exitosas", ok_all, f"{successes}/10", CAT)

    # 5.2 Consistencia — misma entrada → misma salida (determinismo)
    subheader("5.2 Madurez — determinismo del modelo (misma entrada = misma salida)")
    if results_probas and len(results_probas) >= 2:
        all_same = all(abs(p - results_probas[0]) < 1e-6 for p in results_probas)
        result("Modelo determinista (misma entrada = misma probabilidad)", all_same,
               f"valores únicos: {len(set(round(p,6) for p in results_probas))}", CAT)
    else:
        result("Modelo determinista", False, "No hay datos suficientes", CAT)

    # 5.3 Tolerancia a fallos — entrada con valores extremos
    subheader("5.3 Tolerancia a fallos — entradas con valores extremos")
    extreme_cases = [
        ("Temperatura extrema (60°C)", {"grid_id": "EXT-001", "pendiente_pct": 20.0,
            "orientacion": "N", "ndvi": 0.3, "dist_carretera_m": 400.0,
            "dist_poblado_m": 800.0, "temp_2m": 60.0, "humedad_relativa": 5.0,
            "viento_velocidad": 100.0, "viento_direccion": 45.0}),
        ("Humedad 100%", {"grid_id": "EXT-002", "pendiente_pct": 1.0,
            "orientacion": "S", "ndvi": 0.95, "dist_carretera_m": 20000.0,
            "dist_poblado_m": 50000.0, "temp_2m": 5.0, "humedad_relativa": 100.0,
            "viento_velocidad": 0.1, "viento_direccion": 0.0}),
    ]
    for label, body in extreme_cases:
        r = api_post("/predict", body)
        ok = r is not None and r.status_code in [200, 422]
        detail = f"HTTP {r.status_code}" if r else "sin respuesta"
        result(f"No crashea con {label}", ok, detail, CAT)
        if r and r.status_code == 200:
            p = r.json().get("probabilidad", -1)
            in_range = 0.0 <= p <= 1.0
            result(f"Probabilidad en [0,1] con {label}", in_range, f"p={p}", CAT)

    # 5.4 Disponibilidad — /health responde en cada intento
    subheader("5.4 Disponibilidad — /health responde 5/5 veces consecutivas")
    health_ok = 0
    for _ in range(5):
        r = api_get("/health")
        if r and r.status_code == 200:
            health_ok += 1
    ok = health_ok == 5
    result(f"Disponibilidad /health: {health_ok}/5", ok, "", CAT)

    # 5.5 Recuperabilidad — modelo no falla si se consulta status
    subheader("5.5 Recuperabilidad — scheduler de alertas reporta estado")
    r = api_get("/alert/status")
    if r and r.status_code == 200:
        data = r.json()
        ok = "scheduler_activo" in data and "horario" in data
        result("Estado del scheduler reportado correctamente", ok, str(data)[:150], CAT)
    else:
        result("Estado del scheduler reportado correctamente", False,
               f"HTTP {r.status_code if r else 'sin respuesta'}", CAT)

    # 5.6 Integridad del modelo — archivo pkl presente y cargable
    subheader("5.6 Madurez — modelo LightGBM cargable desde disco")
    try:
        model = joblib.load(MODEL_PATH)
        ok_load = model is not None
        result("Modelo .pkl cargado sin error", ok_load, str(MODEL_PATH), CAT)
        has_predict = hasattr(model, "predict_proba")
        result("Modelo tiene método predict_proba()", has_predict, "", CAT)
        model_size_kb = MODEL_PATH.stat().st_size / 1024
        ok_size = model_size_kb > 10
        result(f"Modelo .pkl tiene tamaño razonable (>{10}KB)", ok_size,
               f"{model_size_kb:.1f} KB", CAT)
    except Exception as e:
        result("Modelo .pkl cargado sin error", False, str(e), CAT)


# ─────────────────────────────────────────────────────────────────────────────
# 6. SEGURIDAD
# ─────────────────────────────────────────────────────────────────────────────

def test_security():
    header("6. SEGURIDAD (Security) — ISO 25010 §4.6")
    CAT = "Seguridad"

    # 6.1 CORS no expone información sensible innecesariamente
    subheader("6.1 Confidencialidad — cabeceras de seguridad HTTP")
    r = api_get("/health")
    if r:
        # X-Content-Type-Options
        x_ct = r.headers.get("x-content-type-options", "")
        result("X-Content-Type-Options presente", len(x_ct) > 0,
               f"valor='{x_ct}' (recomendado: nosniff)", CAT)
        # Server info no debe revelar versión exacta
        server = r.headers.get("server", "")
        no_version_leak = not re.search(r'\d+\.\d+', server)
        result("Server header no revela versión exacta", no_version_leak,
               f"server='{server}'", CAT)
    else:
        result("X-Content-Type-Options presente", False, "Sin respuesta", CAT)
        result("Server header no revela versión exacta", False, "Sin respuesta", CAT)

    # 6.2 .env no expuesto vía API
    subheader("6.2 Confidencialidad — archivos .env no accesibles por API")
    for path in ["/.env", "/.env.example", "/app/.env", "/config"]:
        r = api_get(path)
        if r:
            ok = r.status_code in [404, 403, 422]
            result(f"Ruta {path} no es accesible (404/403)", ok, f"HTTP {r.status_code}", CAT)
        else:
            result(f"Ruta {path} no es accesible", True, "Sin respuesta (OK)", CAT)

    # 6.3 Integridad de datos — /predict valida tipos de datos
    subheader("6.3 Integridad — validación de tipos de entrada en /predict")
    bad_payloads = [
        ("String en pendiente_pct", {"grid_id":"T1","pendiente_pct":"MALICIOUS","orientacion":"N",
                                      "ndvi":0.3,"dist_carretera_m":400,"dist_poblado_m":800,
                                      "temp_2m":28,"humedad_relativa":32,
                                      "viento_velocidad":20,"viento_direccion":45}),
        ("Payload vacío", {}),
        ("SQL injection en grid_id", {"grid_id":"'; DROP TABLE grillas;--","pendiente_pct":20,
                                       "orientacion":"N","ndvi":0.3,"dist_carretera_m":400,
                                       "dist_poblado_m":800,"temp_2m":28,"humedad_relativa":32,
                                       "viento_velocidad":20,"viento_direccion":45}),
    ]
    for label, body in bad_payloads:
        r = api_post("/predict", body)
        if r is not None:
            ok = r.status_code in [200, 422, 400]
            result(f"No crashea con {label}", ok, f"HTTP {r.status_code}", CAT)
        else:
            result(f"No crashea con {label}", False, "Sin respuesta", CAT)

    # 6.4 PDF no expone datos privados en metadatos
    subheader("6.4 Confidencialidad — PDF generado no contiene credenciales")
    r = api_get("/report/pdf", timeout=30)
    if r and r.status_code == 200:
        pdf_bytes = r.content
        # Buscar patrones de credenciales en el PDF (en texto plano)
        pdf_text = pdf_bytes.decode("latin-1", errors="ignore")
        has_token = any(t in pdf_text for t in ("WHATSAPP_TOKEN", "GREEN_API_TOKEN", "API_KEY"))
        result("PDF no contiene tokens/API_KEY en texto", not has_token,
               "Búsqueda de WHATSAPP_TOKEN, API_KEY", CAT)
        has_env_vars = re.search(r'[A-Z_]{5,}=\S+', pdf_text) is not None
        result("PDF no contiene variables de entorno", not has_env_vars, "", CAT)
    else:
        result("PDF generado sin error para validar", False,
               f"HTTP {r.status_code if r else 'sin respuesta'}", CAT)

    # 6.5 Autenticidad — OpenAPI especifica info del proyecto
    subheader("6.5 Autenticidad — API identifica claramente el sistema")
    r = api_get("/openapi.json")
    if r and r.status_code == 200:
        schema = r.json()
        title = schema.get("info", {}).get("title", "")
        ok = "alerta" in title.lower() or "wildfire" in title.lower() or "forestal" in title.lower()
        result("Título de la API identifica el sistema correctamente", ok, f"título='{title}'", CAT)
    else:
        result("Título de la API identifica el sistema correctamente", False, "Sin respuesta", CAT)


# ─────────────────────────────────────────────────────────────────────────────
# 7. MANTENIBILIDAD
# ─────────────────────────────────────────────────────────────────────────────

def test_maintainability():
    header("7. MANTENIBILIDAD (Maintainability) — ISO 25010 §4.7")
    CAT = "Mantenibilidad"

    # 7.1 Modularidad — estructura de carpetas del proyecto
    subheader("7.1 Modularidad — estructura de directorios bien organizada")
    expected_dirs = ["app", "web", "data_pipeline", "airflow", "dashboard",
                     "data", "models", "tests", "docs"]
    for d in expected_dirs:
        ok = (ROOT / d).exists()
        result(f"Directorio /{d} existe", ok, "", CAT)

    # 7.2 Modularidad — archivos del backend separados por responsabilidad
    subheader("7.2 Modularidad — separación de responsabilidades (SoC) en /app")
    app_files = {
        "main.py":            "Endpoints de la API (controladores)",
        "model.py":           "Carga y predicción del modelo ML",
        "propagation.py":     "Motor de propagación del fuego",
        "whatsapp_alerts.py": "Integración con WhatsApp",
        "pdf_generator.py":   "Generación de reportes PDF",
        "scheduler.py":       "Scheduler de alertas automáticas",
    }
    for fname, desc in app_files.items():
        ok = (APP_DIR / fname).exists()
        result(f"app/{fname} — {desc}", ok, "", CAT)

    # 7.3 Analizabilidad — presencia de docstrings y comentarios
    subheader("7.3 Analizabilidad — docstrings en módulos del backend")
    for fname in ["main.py", "model.py", "propagation.py"]:
        fpath = APP_DIR / fname
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8")
            has_docstring = '"""' in content or "'''" in content
            result(f"app/{fname} tiene docstrings/comentarios", has_docstring, "", CAT)

    # 7.4 Modificabilidad — no hay código hardcoded de producción crítico en main
    subheader("7.4 Modificabilidad — variables de entorno usadas para configuración")
    main_content = (APP_DIR / "main.py").read_text(encoding="utf-8")
    uses_os_getenv = "os.getenv" in main_content or "os.environ" in main_content
    result("main.py usa os.getenv() para configuración", uses_os_getenv, "", CAT)

    # FIRMS key en main.py vía env var
    firms_uses_env = "os.getenv" in main_content and "FIRMS_MAP_KEY" in main_content
    result("FIRMS_MAP_KEY leído desde variable de entorno", firms_uses_env, "", CAT)

    # 7.5 Testeabilidad — suite de tests existente
    subheader("7.5 Testeabilidad — suite de pruebas presente")
    test_files = list((ROOT / "tests").glob("*.py"))
    ok = len(test_files) >= 2
    result(f"Al menos 2 archivos de prueba en /tests ({len(test_files)} encontrados)", ok,
           str([f.name for f in test_files]), CAT)

    # 7.6 Reusabilidad — requirements.txt con versiones fijadas
    subheader("7.6 Reusabilidad/Portabilidad — requirements.txt presente y completo")
    req = ROOT / "requirements.txt"
    if req.exists():
        content = req.read_text(encoding="utf-8")
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
        result(f"requirements.txt tiene ≥10 dependencias ({len(lines)} encontradas)",
               len(lines) >= 10, str(lines[:5]) + "...", CAT)
        has_versions = any(">=" in l or "==" in l for l in lines)
        result("Dependencias tienen versiones mínimas especificadas", has_versions, "", CAT)
    else:
        result("requirements.txt presente", False, "", CAT)

    # 7.7 .env.example presente para onboarding
    subheader("7.7 Analizabilidad — .env.example para configuración de entorno")
    env_ex = ROOT / ".env.example"
    ok = env_ex.exists()
    result(".env.example existe para onboarding", ok, "", CAT)
    if ok:
        content = env_ex.read_text(encoding="utf-8")
        has_firms = "FIRMS_MAP_KEY" in content
        has_wa = "GREEN_API_INSTANCE_ID" in content and "WHATSAPP_GROUP_IDS" in content
        result(".env.example documenta FIRMS_MAP_KEY", has_firms, "", CAT)
        result(".env.example documenta Green API (GREEN_API_*) + WHATSAPP_GROUP_IDS", has_wa, "", CAT)

    # 7.8 Docker compose presente
    subheader("7.8 Modificabilidad — infraestructura como código (IaC)")
    ok_compose = (ROOT / "docker-compose.yml").exists()
    result("docker-compose.yml presente", ok_compose, "", CAT)
    ok_dockerfile = (ROOT / "Dockerfile").exists()
    result("Dockerfile presente", ok_dockerfile, "", CAT)


# ─────────────────────────────────────────────────────────────────────────────
# 8. PORTABILIDAD
# ─────────────────────────────────────────────────────────────────────────────

def test_portability():
    header("8. PORTABILIDAD (Portability) — ISO 25010 §4.8")
    CAT = "Portabilidad"

    # 8.1 Adaptabilidad — Dockerfile presente y válido
    subheader("8.1 Adaptabilidad — Dockerfile configurable por entorno")
    dockerfile = ROOT / "Dockerfile"
    if dockerfile.exists():
        content = dockerfile.read_text(encoding="utf-8")
        has_from = "FROM" in content
        result("Dockerfile contiene instrucción FROM", has_from, "", CAT)
        has_workdir = "WORKDIR" in content
        result("Dockerfile define WORKDIR", has_workdir, "", CAT)
        has_copy = "COPY" in content or "ADD" in content
        result("Dockerfile copia archivos al contenedor", has_copy, "", CAT)
        has_cmd = "CMD" in content or "ENTRYPOINT" in content
        result("Dockerfile define punto de entrada (CMD/ENTRYPOINT)", has_cmd, "", CAT)
    else:
        result("Dockerfile existe", False, "", CAT)

    # 8.2 Instalabilidad — requirements.txt cubre paquetes clave
    subheader("8.2 Instalabilidad — dependencias cubren todo el stack")
    req = ROOT / "requirements.txt"
    if req.exists():
        content = req.read_text(encoding="utf-8").lower()
        required_pkgs = [
            ("fastapi", "Backend API"),
            ("uvicorn", "Servidor ASGI"),
            ("lightgbm", "Modelo ML"),
            ("pandas", "Procesamiento de datos"),
            ("geopandas", "Datos geoespaciales"),
            ("streamlit", "Dashboard"),
            ("locust", "Pruebas de carga"),
            ("apscheduler", "Scheduler de alertas"),
        ]
        for pkg, desc in required_pkgs:
            ok = pkg in content
            result(f"requirements.txt incluye {pkg} ({desc})", ok, "", CAT)
    else:
        result("requirements.txt existe", False, "", CAT)

    # 8.3 Reemplazabilidad — API sirve portal web directamente (sin servidor externo)
    subheader("8.3 Reemplazabilidad — portal web servido directamente por FastAPI")
    r = api_get("/")
    ok = r is not None and r.status_code == 200 and "text/html" in r.headers.get("content-type","")
    result("FastAPI sirve portal web en / sin servidor externo", ok,
           f"HTTP {r.status_code if r else 'sin respuesta'}", CAT)

    # 8.4 Adaptabilidad — datos en formato estándar (parquet + CSV)
    subheader("8.4 Adaptabilidad — dataset en formatos estándar intercambiables")
    parquet = ROOT / "data" / "dataset.parquet"
    csv = ROOT / "data" / "dataset.csv"
    ok_pq = parquet.exists()
    result("Dataset disponible en formato Parquet (eficiente)", ok_pq,
           f"{parquet.stat().st_size/1024/1024:.1f} MB" if ok_pq else "", CAT)
    ok_csv = csv.exists()
    result("Dataset disponible en formato CSV (universal)", ok_csv,
           f"{csv.stat().st_size/1024/1024:.1f} MB" if ok_csv else "", CAT)

    # 8.5 Portabilidad cross-platform — rutas con pathlib
    subheader("8.5 Portabilidad — rutas de archivo usando pathlib (cross-platform)")
    for fname in ["main.py", "model.py", "propagation.py"]:
        fpath = APP_DIR / fname
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8")
            uses_pathlib = "Path(" in content or "from pathlib" in content
            does_io = any(t in content for t in ("open(", "read_text", "read_csv", "joblib.load", "pickle.load"))
            no_os_paths = ("C:\\" not in content) and ("/home/" not in content) and ("/Users/" not in content)
            ok = no_os_paths and (uses_pathlib or not does_io)
            result(f"app/{fname} portabilidad de rutas (pathlib / sin rutas OS)", ok, "", CAT)


# ─────────────────────────────────────────────────────────────────────────────
# RESUMEN FINAL
# ─────────────────────────────────────────────────────────────────────────────

def print_summary():
    header("RESUMEN EJECUTIVO — AUDITORÍA ISO/IEC 25010")

    total_pass = sum(v[0] for v in score_board.values())
    total_all  = sum(v[1] for v in score_board.values())
    global_pct = (total_pass / total_all * 100) if total_all > 0 else 0

    print(f"\n  Fecha de auditoría : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Sistema auditado   : AlertaForestal Perú v2.0")
    print(f"  URL base           : {BASE_URL}")
    print(f"  Norma aplicada     : ISO/IEC 25010:2011\n")

    sep()
    print(f"  {'Característica':<32} {'Pasa':>6} {'Total':>6} {'%':>7}  {'Calificación'}")
    sep()

    GRADES = {
        range(90, 101): "⭐⭐⭐⭐⭐ Excelente",
        range(75, 90):  "⭐⭐⭐⭐  Bueno",
        range(60, 75):  "⭐⭐⭐   Aceptable",
        range(40, 60):  "⭐⭐    Mejorable",
        range(0,  40):  "⭐     Crítico",
    }

    def grade(pct):
        for r, label in GRADES.items():
            if int(pct) in r:
                return label
        return "⭐ Crítico"

    for cat, (passed, total) in sorted(score_board.items()):
        pct = (passed / total * 100) if total > 0 else 0
        g = grade(pct)
        print(f"  {cat:<32} {passed:>6}/{total:<6} {pct:>6.1f}%  {g}")

    sep()
    g_global = grade(global_pct)
    print(f"  {'TOTAL GLOBAL':<32} {total_pass:>6}/{total_all:<6} {global_pct:>6.1f}%  {g_global}")
    sep()

    if global_pct >= 80:
        verdict = "✅ SISTEMA APROBADO según ISO/IEC 25010"
    elif global_pct >= 60:
        verdict = "⚠️  SISTEMA CONDICIONAL — requiere mejoras menores"
    else:
        verdict = "❌ SISTEMA REPROBADO — requiere mejoras críticas"

    print(f"\n  {verdict}\n")
    print("=" * 80)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("  🔥 AUDITORÍA ISO/IEC 25010 — AlertaForestal Perú")
    print("  Sistema Nacional de Alerta Temprana de Incendios Forestales")
    print("=" * 80)
    print(f"\n  Conectando a {BASE_URL} ...")

    # Verificar conectividad
    r = api_get("/health")
    if r is None:
        print(f"\n  ⚠️  ADVERTENCIA: No se pudo conectar a {BASE_URL}")
        print("  Algunas pruebas de API se marcarán como FALLA.")
        print("  Las pruebas locales (modelo, archivos) se ejecutarán igualmente.\n")
    else:
        print(f"  ✅ API responde: HTTP {r.status_code}\n")

    test_functional_suitability()
    test_performance_efficiency()
    test_compatibility()
    test_usability()
    test_reliability()
    test_security()
    test_maintainability()
    test_portability()
    print_summary()
