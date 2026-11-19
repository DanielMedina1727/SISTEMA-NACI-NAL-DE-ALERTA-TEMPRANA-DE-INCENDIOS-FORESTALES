"""
Pruebas de sistema y aceptación (E2E) alineadas a los criterios CR01–CR09
del curso Capstone Project Sistemas (INVE1535 — UPN).

Valida flujos completos sin servidor externo usando FastAPI TestClient:
  - CR01: Integración de las 5 fuentes y 18 variables predictoras.
  - CR02: Cobertura territorial de Cajamarca (~67 640 celdas analizadas).
  - CR03: Clasificación de susceptibilidad diaria en 3 niveles y /healthz.
  - CR04: Métricas honestas sin fuga espacial registradas en metadatos.
  - CR05: Portal web ciudadano servido en /web/ con límite oficial INEI (118 vértices).
  - CR06: Motor de propagación, alertas diarias (/alert/status) y reporte PDF.
  - CR07: Trazabilidad completa de predicciones (grid_id, score, percentil, metadata).
  - CR08: Cabeceras de seguridad HTTP y minimización de datos personales.
  - CR09: Transparencia y matriz de responsabilidad social (/social/matrix).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from conftest import requires_dataset, requires_model
from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parent.parent
METADATA_PATH = ROOT / "models" / "model_metadata.json"
WEB_DIR = ROOT / "web"

client = TestClient(app)


# ── CR01: Integración de 5 fuentes y 18 variables ─────────────────────────────
@requires_model
def test_cr01_five_sources_and_features():
    from app.model import FEATURE_ORDER

    assert METADATA_PATH.exists(), "Debe existir models/model_metadata.json"
    meta = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    assert len(meta["features"]) == len(FEATURE_ORDER)
    assert len(meta["feature_sources"]) == 5
    for key in ("terreno", "vegetacion", "meteorologia", "infraestructura", "etiqueta"):
        assert key in meta["feature_sources"]


# ── CR02: Cobertura territorial de Cajamarca ──────────────────────────────────
@requires_model
@requires_dataset
def test_cr02_cajamarca_territorial_coverage():
    r = client.get("/risk/today", params={"limit": 100})
    assert r.status_code == 200
    stats = r.json()["stats"]
    assert stats["total_analizado"] >= 60_000
    assert stats["rojo"] + stats["amarillo"] + stats["verde"] == stats["total_analizado"]


# ── CR03: Healthcheck nube (/healthz) y clasificación en 3 niveles ────────────
def test_cr03_healthz_cloud_alias():
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "model_version" in body


# ── CR04: Métricas honestas registradas en metadatos ──────────────────────────
def test_cr04_honest_spatial_metrics_in_metadata():
    meta = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    opt = meta["metrics"]["optimized_ensemble"]
    assert 0.5 < opt["roc_auc"] < 0.99, "ROC-AUC debe superar al azar sin fuga de datos"
    assert opt["average_precision"] > meta["random_baseline_precision"]
    assert opt["recall_at_top_10pct"] > 0.10
    assert opt["recall_at_top_20pct"] > 0.20


# ── CR05: Portal web ciudadano servido y límite oficial INEI ──────────────────
def test_cr05_web_portal_served_and_official_inei_border():
    r = client.get("/web/")
    assert r.status_code == 200
    html = r.text
    assert "AlertaForestal" in html
    assert "reportForm" in html
    assert "como-usar" in html

    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    assert "CAJAMARCA_BORDER" in app_js
    assert "INEI" in app_js
    # Verificar que el polígono oficial tenga los 118 vértices
    block = app_js.split("const CAJAMARCA_BORDER = [", 1)[1].split("];", 1)[0]
    coords = re.findall(r"\[-?\d+\.\d+,-?\d+\.\d+\]", block)
    assert len(coords) == 118


# ── CR06: Estado del scheduler diario de alertas ──────────────────────────────
def test_cr06_alert_scheduler_status():
    r = client.get("/alert/status")
    assert r.status_code == 200
    body = r.json()
    assert "scheduler_activo" in body
    assert "zona_horaria" in body


# ── CR06b: Motor de propagación espacial por viento ───────────────────────────
def test_cr06_propagation_engine_returns_affected_grids():
    r = client.post(
        "/propagate",
        params={
            "grid_id": "-78.5000_-7.1500",
            "viento_direccion": 45.0,
            "viento_velocidad": 20.0,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["origen"] == "-78.5000_-7.1500"
    assert len(body["grillas_afectadas"]) >= 1


# ── CR06c: Generación de reporte ejecutivo PDF ────────────────────────────────
def test_cr06_pdf_executive_report_generated():
    r = client.get("/report/pdf")
    assert r.status_code == 200
    assert "application/pdf" in r.headers.get("content-type", "")
    assert r.content.startswith(b"%PDF")
    assert len(r.content) > 1500


# ── CR07: Trazabilidad completa de predicción individual ──────────────────────
@requires_model
def test_cr07_prediction_traceability_fields():
    r = client.post(
        "/predict",
        json={
            "grid_id": "-78.5000_-7.1600",
            "temp_2m": 26.5,
            "humedad_relativa": 30.0,
            "pendiente_pct": 22.0,
        },
    )
    assert r.status_code == 200
    body = r.json()
    for field in ("grid_id", "probabilidad", "nivel", "percentil"):
        assert field in body, f"Falta campo de trazabilidad: {field}"
    assert 0.0 <= body["percentil"] <= 100.0
    health = client.get("/health").json()
    assert set(health["thresholds"]) == {"rojo", "amarillo"}


# ── CR08: Cabeceras HTTP de seguridad (OWASP / Plan de Seguridad Integral) ────
def test_cr08_security_headers_present():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") in {"DENY", "SAMEORIGIN"}
    assert "referrer-policy" in r.headers


# ── CR08b: Minimización de datos personales en esquema CitizenReport ──────────
def test_cr08_citizen_report_data_minimization():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()["components"]["schemas"]["CitizenReport"]["properties"]
    for forbidden in ("nombre", "name", "dni", "telefono", "phone", "email", "correo"):
        assert forbidden not in schema, f"No debe solicitar dato personal: {forbidden}"


# ── CR09: Matriz de entorno social y transparencia ciudadana ──────────────────
def test_cr09_social_matrix_endpoint():
    r = client.get("/social/matrix")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    assert len(body) >= 1
