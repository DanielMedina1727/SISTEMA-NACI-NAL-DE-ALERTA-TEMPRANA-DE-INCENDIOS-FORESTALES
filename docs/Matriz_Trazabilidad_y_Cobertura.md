# Matriz de Trazabilidad y Cobertura de Requisitos

> **Curso:** Capstone Project Sistemas (INVE1535 — 10° Ciclo, 2026-2, UPN)
> **Proyecto:** AlertaForestal Perú — Sistema web para la predicción de incendios forestales en Cajamarca
> **Evidencia del Sílabo:** Semana 4 (Matriz de trazabilidad problema-necesidades-requisitos-diseño) y Semana 9 (Matriz de cobertura de requisitos)

---

## 1. Matriz de Trazabilidad Completa (Problema → Necesidad → Requisito → Diseño → Prueba)

| Problema (Pareto) | Necesidad | Requisito / HU | Componente / Módulo de Diseño | Pruebas Automatizadas que lo Verifican | Criterio | Estado |
|---|---|---|---|---|---|---|
| **P1** Fragmentación de datos (38%) | **N01** Información territorial integrada | **RF-01** Ingesta NASA FIRMS | `data_pipeline/fetch_firms.py`, `app/main.py` (`/firms/hotspots`) | `test_acceptance.py::test_cr01_five_sources_and_18_features` | CR01 | ✅ Cumple |
| **P1 / P3** Falta de integración clima-SIG | **N01** Variables atmosféricas y SIG | **RF-02 / RF-03** ERA5 + DEM + NDVI + OSM | `data_pipeline/real_features.py`, `data_pipeline/fetch_era5.py` | `test_pipeline.py` (5 tests), `test_cr01_five_sources_and_18_features` | CR01 | ✅ Cumple |
| **P3** Sin zonificación espacial (16%) | **N02** Identificación anticipada por grilla | **RF-04** Grilla ~1 km² (68 187 celdas) | `data_pipeline/grid_builder.py`, `data/dataset.parquet` | `test_acceptance.py::test_cr02_cajamarca_territorial_coverage` | CR02 | ✅ Cumple |
| **P3** Sin modelo predictivo integrado | **N02 / N05** Estimación y trazabilidad | **RF-05** Ensemble LightGBM+XGB+RF + SHAP | `data_pipeline/train_model.py`, `app/model.py`, `models/` | `test_model.py` (10 tests), `test_cr04_honest_spatial_metrics_in_metadata` | CR03/CR04 | ✅ Cumple (CR03 parcial: 1 fecha ref.) |
| **P1 / P2** Acceso disperso | **N03** Visualización y acceso rápido | **RF-06** API REST OpenAPI | `app/main.py` (`/health`, `/healthz`, `/predict`, `/risk/today`, `/propagate`) | `test_api.py` (13 tests), `test_cr03_healthz_cloud_alias`, `test_cr07_prediction_traceability_fields` | CR05/CR07 | ✅ Cumple |
| **P5** Dificultad para priorizar recursos (8%) | **N03** Mapa comprensible sin registro | **RF-07 / RF-08** Portal Web + Leaflet + Límite INEI | `web/index.html`, `web/app.js`, `web/styles.css` | `test_acceptance.py::test_cr05_web_portal_served_and_official_inei_border` | CR05 | ✅ Cumple |
| **P2** Retraso en reportes de campo (26%) | **N04** Reporte ágil comunitario | **RF-09** Reporte ciudadano georreferenciado | `app/main.py` (`/report/citizen`, `/report/recent`), `app/zones.py` | `test_api.py` (5 tests citizen/zone), `test_cr08_citizen_report_data_minimization` | CR06/CR08 | ✅ Cumple |
| **P4** Alertas tardías (12%) | **N04** Alertamiento prioritario | **RF-10** Alertas WhatsApp 07:00 (Green API) | `app/scheduler.py`, `app/whatsapp_alerts.py` | `test_whatsapp_multi.py` (12 tests), `test_cr06_alert_scheduler_status` | CR06 | ✅ Cumple (requiere env vars Green API) |
| **P5** Falta de reportes ejecutivos | **N03 / N05** Expediente y trazabilidad | **RF-11** Reportes ejecutivos PDF | `app/pdf_generator.py` (`/report/pdf`) | `test_acceptance.py::test_cr06_pdf_executive_report_generated` | CR05/CR07 | ✅ Cumple |
| **P4 / P5** Transparencia y ética | **N05** Explicabilidad y entorno social | **RF-12** `/model/importance`, `/social/matrix`, `/propagate` | `app/main.py`, `app/propagation.py` | `test_api.py::test_model_importance_shape`, `test_cr06_propagation_engine_returns_affected_grids`, `test_cr09_social_matrix_endpoint` | CR07/CR09 | ✅ Cumple (validación campo pendiente) |
| **Seguridad / Legal** | Protección credenciales y datos (Ley 29733) | **RNF-03** API Key, CORS, Rate Limit, BBox, Headers | `app/security.py`, `app/main.py` (`add_security_headers`) | `test_security.py` (6 tests), `test_cr08_security_headers_present`, `test_cr08_citizen_report_data_minimization` | CR08 | ✅ Cumple |

---

## 2. Resumen de Cobertura de Requisitos

| Categoría | Total Definidos | Implementados | Cubiertos por Pruebas | Cobertura |
|---|---|---|---|---|
| Requerimientos Funcionales (`RF-01` a `RF-12`) | 12 | 12 | 12 | **100 %** |
| Requerimientos No Funcionales (`RNF-01` a `RNF-06`) | 6 | 6 | 6 | **100 %** |
| Criterios de Aceptación (`CR01` a `CR09`) | 9 | 9 (7 completos + 2 parciales con justificación técnica/campo) | 9 | **100 %** |
| Historias de Usuario (`docs/Historias_de_Usuario.md`) | 74 (66 HU + 8 RNF) | 33 Must / 30 Should implementados | 58 pruebas automatizadas | **100 % MVP** |
