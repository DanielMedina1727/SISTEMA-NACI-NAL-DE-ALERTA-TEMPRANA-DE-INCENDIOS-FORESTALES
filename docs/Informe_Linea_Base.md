# Informe de Línea Base del Capstone Project

> **Curso:** Capstone Project Sistemas (INVE1535 — 10° Ciclo, 2026-2, UPN)
> **Evidencia del Sílabo:** Semana 15 (Presentación de informe de Línea Base del Capstone Project)
> **Proyecto:** AlertaForestal Perú — Sistema web para la predicción de incendios forestales en Cajamarca

---

## 1. Línea Base de Alcance

- **Objetivo general:** Determinar la influencia de un sistema web basado en sensores remotos y variables atmosféricas en la precisión de la estimación del riesgo de incendios forestales en Cajamarca.
- **Productos entregados (MVP + mejoras):**
  1. Pipeline ETL reproducible para 5 fuentes abiertas (NASA FIRMS, ERA5/Open-Meteo, Copernicus DEM GLO-30, Sentinel-2 L2A, OpenStreetMap) y grilla de 68 187 celdas (~1 km²).
  2. Modelo ensemble (`v2.3.0-spatial-ensemble-real`: LightGBM + XGBoost + Random Forest) validado espacialmente (5-fold GroupKFold, bloques de 50 km) con SHAP.
  3. API REST en FastAPI con documentación OpenAPI (`/docs`), healthchecks (`/health`, `/healthz`), propagación (`/propagate`), reportes PDF (`/report/pdf`) y reportes ciudadanos (`/report/citizen`).
  4. Portal web ciudadano sin registro con Leaflet, límite departamental oficial INEI (118 vértices), semáforo calibrado y guía ciudadana paso a paso.
  5. Sistema de alertas diarias WhatsApp (07:00 America/Lima) vía Green API con soporte multi-instancia.
  6. Despliegue en la nube en Render (`https://alerta-temprana-de-incendios-forestales.onrender.com/web/`) y contenedor Docker reproducible.
- **Fuera de alcance:** Extinción física en campo, instalación de sensores IoT propios, integración oficial con sistemas estatales (SINAGERD/COEN), pronóstico determinista de ignición a 24–48 h.

---

## 2. Línea Base de Cronograma (16 Semanas — 8 Sprints)

| Hito | Semana | Entregable de Línea Base | Estado |
|---|---:|---|---|
| **H1** | S02 | Business Case, diagnóstico Pareto/Ishikawa, requisitos y backlog (74 HU/RNF) | ✅ Completado |
| **H2** | S06 | Ingesta de 5 fuentes, grilla `dataset.parquet` (68 187 × 30) y 18 features | ✅ Completado |
| **H3** | S09 | Modelo v2.3.0 entrenado, validación espacial sin fuga y métricas honestas | ✅ Completado |
| **H4** | S12 | API FastAPI, portal Leaflet con límite INEI, reportes ciudadanos, PDF y WhatsApp | ✅ Completado |
| **H5** | S14 | 58 pruebas automatizadas (4 niveles), CI/CD GitHub Actions, SQA y despliegue Render | ✅ Completado |
| **H6** | S16 | Informe final alineado al sílabo, sustentación y evidencias en Blackboard | 🔄 En cierre |

---

## 3. Línea Base de Costos

| Concepto | Presupuesto Planificado (S/) | Ejecutado Real (S/) | Variación |
|---|---:|---:|---|
| Equipos de cómputo (5 laptops propias valorizadas) | 15 000 | 15 000 (valorizado) | S/ 0 |
| Infraestructura cloud (Render Free Tier / pruebas) | 420 | 0 (plan gratuito) | -S/ 420 |
| Internet y conectividad (6 meses) | 600 | 600 | S/ 0 |
| Dominio .pe + TLS | 120 | 0 (subdominio `.onrender.com` + TLS) | -S/ 120 |
| Fuentes de datos y APIs abiertas | 0 | 0 | S/ 0 |
| Validación, materiales y capacitación | 300 | 300 (estimado cierre) | S/ 0 |
| Imprevistos (10%) | 144 | 0 | -S/ 144 |
| **Total Operativo** | **1 584** | **900** | **-43.2 % (bajo presupuesto)** |

---

## 4. Línea Base Técnica y de Configuración (Antes vs. Después)

| Indicador | Línea Base (Antes) | Línea Base Final (v2.3.0) |
|---|---|---|
| ROC-AUC espacial | 0.413 (baseline tutorial) / 0.500 (azar) | **0.6489 ± 0.0685** |
| PR-AUC | 0.0006 (prevalencia 0.00066) | **0.0017 ± 0.0015** (2.6× azar) |
| Recall@Top-10% / Top-20% | 10% / 20% (azar) | **19.44% / 45.11%** |
| Cobertura territorial automatizada | 0 celdas (proceso manual) | **67 640 celdas (~1 km²)** |
| Pruebas automatizadas | 0 | **58/58 passed (4 niveles)** |
| Errores análisis estático (`ruff`) | No medido | **0 errores** |
| Repositorio y rama base | `main` en GitHub (`DanielMedina1727/...`) | Versionado con CI en GitHub Actions |
