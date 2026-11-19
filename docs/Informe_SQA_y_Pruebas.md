# Informe de Revisión SQA y Reporte de Pruebas de Software

> **Curso:** Capstone Project Sistemas (INVE1535 — 10° Ciclo, 2026-2, UPN)
> **Evidencia del Sílabo:** Semanas 9, 11 y 15 (Pruebas unitarias, integración, sistema, aceptación + Revisión SQA + Registro de defectos)
> **Versión auditada:** `v2.3.0` (desplegada en Render y verificada en local)

---

## 1. Alcance de la Revisión SQA (ISO/IEC 25010:2023)

Se auditó el producto **AlertaForestal Perú** en sus ocho características de calidad: adecuación funcional, eficiencia de desempeño, compatibilidad, usabilidad, fiabilidad, seguridad, mantenibilidad y portabilidad.

### Herramientas de Aseguramiento de Calidad (SQA)
- **Pruebas automatizadas:** `pytest 9.0.3` (58 pruebas en 6 suites)
- **Análisis estático (Lint):** `ruff` (reglas `E`, `F`, `W`, bugs de imports y código muerto)
- **Integración Continua (CI):** GitHub Actions (`.github/workflows/ci.yml`) en cada `push` y `pull_request`
- **Pruebas de carga:** `Locust` (`tests/locustfile.py`)
- **Auditorías de cumplimiento ISO/IEC 25010:** `tests/audit_quick.py`, `tests/audit_final.py`, `tests/iso25010_audit.py`

---

## 2. Resultados por Nivel de Prueba (Sílabo Semana 9)

| Nivel de Prueba | Suite (`tests/`) | N.º Pruebas | Resultado | Tiempo | Qué verifica |
|---|---|---:|---|---:|---|
| **Unitarias** | `test_model.py` | 10 | ✅ 10/10 | < 1 s | Features, codificación viento, umbrales, percentil, metadatos |
| **Unitarias** | `test_pipeline.py` | 5 | ✅ 5/5 | < 1 s | Vecindario KNN geográfico, ausencia de fuga espacial |
| **Unitarias** | `test_whatsapp_multi.py` | 12 | ✅ 12/12 | < 1 s | Reparto multi-instancia Green API, reintentos, sanitización de tokens |
| **Integración** | `test_api.py` | 13 | ✅ 13/13 | < 1 s | Endpoints REST, reportes ciudadanos, zonas Cajamarca, auth alertas |
| **Integración** | `test_security.py` | 6 | ✅ 6/6 | < 1 s | CORS restringido, rate limit por IP, bounding box Perú, API Key |
| **Sistema y Aceptación** | `test_acceptance.py` | 12 | ✅ 12/12 | < 1 s | Criterios CR01–CR09, portal `/web/`, límite INEI 118 vértices, PDF, `/propagate`, `/healthz`, headers HTTP, minimización datos |
| **TOTAL** | **6 suites** | **58** | **✅ 58/58 (100%)** | **3.25 s** | **Cobertura integral en CI/CD** |

### Análisis Estático y Auditorías Complementarias
- **`ruff check .`**: **0 errores** (`All checks passed!`)
- **Auditorías ISO/IEC 25010**: `audit_quick` **85/85**, `audit_final` **106/106**, `iso25010_audit` **133/133**
- **Pruebas de desempeño**: `/predict` ≈ **32.3 ms**; `/risk/today` (1 200 celdas) ≈ **127 ms**; arranque en caché < 5 s.

---

## 3. Registro de Defectos Detectados y Corregidos en Revisión SQA

| ID | Módulo | Severidad | Defecto Detectado | Acción Correctiva | Estado |
|---|---|---|---|---|---|
| DEF-01 | `app/main.py` | Alta | `AttributeError` en `/alert/status` cuando `job.next_run_time` no existe antes de iniciar el scheduler | Uso seguro de `getattr(job, "next_run_time", None)` | ✅ Cerrado |
| DEF-02 | `app/main.py` | Media | Faltaba cabecera `Referrer-Policy` declarada en el Plan de Seguridad (Tabla 5.7) | Agregada cabecera `Referrer-Policy: strict-origin-when-cross-origin` en middleware | ✅ Cerrado |
| DEF-03 | `scripts/completar_informe.py` | Baja | 2 variables no usadas (`F841`) rompían `ruff check .` en CI | Variables eliminadas; `ruff check .` = 0 errores | ✅ Cerrado |
| DEF-04 | `web/app.js` | Media | Límite de Cajamarca usaba rectángulo aproximado; semáforo marcaba ALTO con ≥3 celdas; demo FIRMS generaba focos ficticios | Reemplazado por polígono oficial INEI (118 vértices), umbral calibrado (≥2% Rojo) y mapa limpio sin datos ficticios | ✅ Cerrado |
| DEF-05 | `Dockerfile` | Baja | Caracteres UTF-8 corruptos en logs de producción | Agregados `ENV PYTHONIOENCODING=utf-8` y `LANG=C.UTF-8` | ✅ Cerrado |
| DEF-06 | `README.md` / `Memoria_Tecnica` | Media | Desfase de métricas (0.61 vs 0.649) y conteo de pruebas (13 vs 58) | Documentación sincronizada con `models/model_metadata.json` y suite actual | ✅ Cerrado |
| DEF-07 | Operación Render | Alta | Envío WhatsApp devuelve `skipped` si no se configuran `GREEN_API_*` y `WA_GROUP_*` en Render; instancia 2 `notAuthorized` | Documentado en `docs/RENDER_ENV_VARS.md`; pendiente carga manual en panel Render y re-escaneo QR de instancia 2 | ⚠️ Acción operativa |

---

## 4. Dictamen SQA

El software **APRUEBA** la revisión técnica de calidad (58/58 pruebas automatizadas, 0 errores de análisis estático, despliegue verificado en Render en `/health`, `/healthz`, `/web/`, `/risk/today`, `/report/pdf`, `/propagate`). Las únicas observaciones pendientes son de carácter operativo/campo (configuración de variables secretas en Render y aplicación de encuestas de satisfacción con usuarios finales).
