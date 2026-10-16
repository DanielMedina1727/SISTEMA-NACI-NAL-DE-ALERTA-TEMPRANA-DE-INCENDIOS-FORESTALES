# 🔥 AlertaForestal Perú — Sistema Nacional de Alerta Temprana de Incendios Forestales

Portal ciudadano y API que calcula un **índice diario de susceptibilidad** y clasifica zonas geográficas (grillas de ~1 km²) en 3 niveles de riesgo (**Verde / Amarillo / Rojo**) para la fecha de referencia, integrando focos satelitales de NASA FIRMS (VIIRS, usados como etiqueta), variables atmosféricas de ERA5 (vía Open-Meteo), topografía de Copernicus DEM GLO-30, vegetación de Sentinel-2 (NDVI) e infraestructura de OpenStreetMap.

---

## 📌 Tabla de Contenidos
- [Descripción del Proyecto](#-descripción-del-proyecto)
- [Portal Web Ciudadano](#%EF%B8%8F-portal-web-ciudadano)
- [Arquitectura y Funcionamiento](#%EF%B8%8F-arquitectura-y-funcionamiento)
- [Stack Tecnológico](#%EF%B8%8F-stack-tecnológico)
- [Estructura del Repositorio](#-estructura-del-repositorio)
- [Guía de Instalación y Uso](#-guía-de-instalación-y-uso)
- [Endpoints de la API](#-endpoints-de-la-api)
- [Semáforo y Umbrales de Riesgo](#-semáforo-y-umbrales-de-riesgo)
- [Pruebas y Auditorías](#-pruebas-y-auditorías)

---

## 🌲 Descripción del Proyecto

**AlertaForestal Perú** es una plataforma ciudadana y comunitaria de monitoreo, prevención y alerta temprana de incendios forestales. El sistema:

- Calcula un **índice diario de susceptibilidad** (ranking relativo) por celda de ~1 km² a partir de datos satelitales, meteorológicos y de terreno reales.
- Expone un **portal web ciudadano** de acceso abierto con mapa interactivo.
- Consume focos VIIRS reales desde **NASA FIRMS** a través de un proxy FastAPI (la API key vive solo en el backend).
- Integra un motor de propagación del fuego simulado basado en pendiente y viento.
- Genera reportes ejecutivos en PDF y **alertas** por WhatsApp (endpoints protegidos por API key).
- Envía un **resumen diario automático** a los grupos comunitarios de WhatsApp a las 07:00 (Lima, UTC-5).

> **Honestidad del dato:** El sistema **no es un pronóstico a 24/48 h**. Es un **índice de susceptibilidad** del día de referencia (ranking relativo por percentil) entrenado con pocos positivos reales (45 focos FIRMS). El mapa distingue datos reales (API activa) de datos de referencia (API offline).

---

## 🗺️ Portal Web Ciudadano

El portal está disponible en **`http://localhost:5050`** al iniciar la API.

| Sección | Tag | Descripción |
|---|---|---|
| **Hero / Inicio** | `#hero` | Indicador de riesgo del día, métricas del día y accesos directos |
| **Mapa en Vivo** | `#mapa` | Grillas de riesgo IA + focos VIIRS reales de NASA FIRMS con filtros de región y ventana de focos (24–72 h) |
| **Alertas WhatsApp** | `#whatsapp` | Suscripción por zona/provincia con QR, flujo de información y protocolo de difusión responsable |
| **Reportar Foco** | `#reporte` | Formulario ciudadano con selección GPS, clic en mapa mini-interactivo y carga de fotos |
| **Centro de Recursos** | `#recursos` | Guías de prevención, widget meteorológico FWI en vivo y directorio de emergencias |
| **Transparencia** | `#transparencia` | Fuentes de datos, métricas del modelo LightGBM y declaración de interés público |

### Métricas del día (Hero)

| Métrica | Descripción |
|---|---|
| 🛰️ **Focos VIIRS Reales** | Focos de calor activos detectados por satélite hoy |
| 🔴 **Zonas Alto Riesgo** | Grillas en el Top-1% de probabilidad del modelo (presupuesto de alerta) |
| 🟡 **Vigilancia** | Grillas en el Top-5% de probabilidad |
| 📊 **Zonas Monitoreadas** | Total de grillas analizadas |
| 📅 **Riesgo del día** | Clasificación diaria (modelo ensemble) para grillas de ~1 km² |

### Capas del Mapa Interactivo

- 🌡️ **Mapa de Calor** — Heatmap de probabilidad de incendio
- 🟥 **Zonas IA** — Grillas coloreadas por nivel de riesgo (Rojo / Amarillo / Verde)
- 🛰️ **Focos Reales VIIRS** — Puntos satelitales de NASA FIRMS con confianza, FRP, satélite y hora

### Simbología

| Color | Criterio (presupuesto de alerta) | Significado |
|---|---|---|
| 🔴 Rojo | Top 1% de celdas por score del modelo | Riesgo muy alto — acción inmediata |
| 🟡 Amarillo | Top 5% de celdas por score | Bajo observación — vigilancia activa |
| 🟢 Verde | Resto del territorio | Riesgo bajo |
| 📍 Punto | — | Foco VIIRS real detectado vía NASA FIRMS |

### Estados del mapa

- **Banner de aviso** `⚠️ API offline`: La API no está activa; se muestran predicciones simuladas y coordenadas de referencia.
- **Banner verde** `✅ Modelo de IA activo` *(se auto-oculta en 4s)*: API activa con datos reales del modelo (ensemble).
- **Popup verde** `✅ Foco Satelital REAL`: Foco detectado por NASA FIRMS hoy.
- **Popup amarillo** `📋 Foco de Referencia`: Solo aparece cuando la API no está disponible.

### Red Comunitaria WhatsApp

Grupos activos por provincia (Cajamarca):

| Provincia | Enlace |
|---|---|
| San Marcos | `chat.whatsapp.com/KwUi6b2Ty7DE0P3kngZnIc` |
| San Pablo | `chat.whatsapp.com/FpO9Etz6KVo1zY0iLZCaIh` |
| Bambamarca | `chat.whatsapp.com/GW6UZu8ywvTJqpKJhrqsSc` |
| Celendín | `chat.whatsapp.com/CYgwoRd1TL88ZV1tvtIr5D` |
| Chota | `chat.whatsapp.com/FSlnpXkSzgz1NdR6qQRMJp` |
| Cajamarca | `chat.whatsapp.com/GDvHyn0XVrf1WeRac1cDrC` |

El resumen diario se envía automáticamente a las **07:00 hora Lima (UTC-5)** con el nivel de riesgo y focos VIIRS del día.

---

## ⚙️ Arquitectura y Funcionamiento

El flujo de trabajo se compone de 5 módulos principales:

1. **Ingesta y Orquestación de Datos (ETL)**
   - **NASA FIRMS**: Focos de calor VIIRS/MODIS satelitales casi en tiempo real (NRT) — usados como **etiqueta** del modelo.
   - **ERA5 vía Open-Meteo**: Variables meteorológicas (temperatura, humedad, viento, lluvia).
   - **Copernicus DEM GLO-30**: Elevación, pendiente y aspecto del terreno.
   - **Sentinel-2 L2A (STAC AWS)**: Índice de vegetación NDVI.
   - **OpenStreetMap Overpass**: Distancia a vías y poblados.
   - **Apache Airflow**: DAGs para ejecución periódica y automatizada.

2. **Almacenamiento**
   - **Parquet / CSV** (en `data/`): dataset de entrenamiento (~68 000 grillas × ~30 columnas) y caché de features en `data/cache/`. El sistema funciona 100 % con estos archivos; **no requiere base de datos**.

3. **Machine Learning y Simulación**
   - **Ensemble (LightGBM + XGBoost + RandomForest)**: índice de susceptibilidad (Verde / Amarillo / Rojo) con **18 variables** reales. Sin calibración de probabilidades. Hiperparámetros optimizados con **Optuna** (objetivo: ROC-AUC espacial) e interpretabilidad con **SHAP**.
   - **Sin fuga de vecindario:** las medias de vecindario se calculan con **KNN geográfico** (no con el bloque de validación) y la dirección del viento se codifica como **sin/cos** (variable circular). `mes_sin`/`mes_cos` se descartaron por ser constantes con una única fecha de referencia (desajuste train/serve).
   - **Evaluación honesta (out-of-fold, 5-fold espacial por bloques de 50 km):** ROC-AUC **0.65 ± 0.07**, **PR-AUC 0.0017** (azar ≈ prevalencia 0.00066), Recall @ Top-1 % **1.0 %**, Top-5 % **5.1 %**, Top-10 % **19.4 %**, Top-20 % **45.1 %**; inferencia < 2 ms por celda. Con solo 45 positivos, un ROC-AUC alto no implica buena precisión en el top; por eso se reporta el PR-AUC.
   - **Semáforo por presupuesto de alerta:** Rojo = Top-1 % de celdas por score, Amarillo = Top-5 %. Umbrales *data-driven* en `models/model_metadata.json`; también se guardan `oof_thresholds` (escala out-of-fold) como referencia honesta.
   - **Soporte multi-fecha:** `grid_builder.py` acepta `--ref-dates` y `fetch_firms.py` acepta `--start-date` para construir un **panel temporal** y reducir el desajuste train/serve. (Ver `docs/Memoria_Tecnica_Capstone.md`.)
   - **Motor de Propagación**: Simulación de dirección y velocidad del fuego según viento y topografía (`SciPy`).

4. **API Backend (FastAPI)**
   - Proxy para NASA FIRMS (la API key vive solo en el backend) y **CORS con lista blanca**.
   - Endpoints de predicción, propagación, reportes PDF y alertas WhatsApp (**protegidos con `X-API-Key`** si `ADMIN_API_KEY` está definida).
   - Rate-limit y validación geográfica en el endpoint de reportes ciudadanos.
   - Scheduler automático de alertas diarias a todos los grupos comunitarios.

5. **Portal Web y Visualización**
   - Frontend HTML/CSS/JS con Leaflet para el mapa interactivo.
   - Dashboard Streamlit con Folium y Plotly.

---

## 🛠️ Stack Tecnológico

| Capa | Herramienta / Librería | Función Principal |
|---|---|---|
| **Orquestación ETL** | Apache Airflow | Automatización y programación de pipelines |
| **Machine Learning** | LightGBM, XGBoost, Scikit-Learn, Optuna, SHAP | Ensamble de clasificación, búsqueda de hiperparámetros e interpretabilidad |
| **Procesamiento Espacial** | GeoPandas, Shapely, Rasterio, SciPy (cKDTree) | Vectores, ráster y vecindario geográfico |
| **Backend API** | FastAPI, Uvicorn | API REST de alto rendimiento |
| **Seguridad API** | FastAPI `Depends` + limitador en memoria | API key (`X-API-Key`), CORS con lista blanca, rate-limit y validación geográfica |
| **Portal Web** | HTML5, CSS3, JavaScript, Leaflet | Portal ciudadano de acceso abierto |
| **Dashboard Interno** | Streamlit, Folium, Plotly | Dashboard técnico interactivo |
| **Datos Satelitales** | NASA FIRMS (VIIRS/MODIS) | Focos de calor NRT (etiqueta del modelo) |
| **Alertas & Reportes** | Green API (WhatsApp), ReportLab | Notificaciones automáticas y PDF ejecutivo |
| **Pruebas de Carga** | Locust | Evaluación de rendimiento y concurrencia |
| **Despliegue** | Docker & Docker Compose | Contenedorización de la infraestructura |

---

## 💻 Herramientas y Programas Necesarios

1. **Python 3.11+**: Lenguaje base para pipelines, API, modelo y dashboard.
2. **Docker Desktop** *(opcional)*: Solo para el contenedor de la API (`docker compose up -d`). El sistema corre sin Docker.
3. **VS Code** o **Cursor**: Editor de código recomendado.
4. **QGIS** *(opcional)*: SIG para inspeccionar GeoTIFFs y grillas de 1 km².
5. **Postman** o **Insomnia**: Para pruebas manuales de endpoints FastAPI.
6. **Git / GitHub Desktop**: Control de versiones y sincronización.

---

## 📂 Estructura del Repositorio

```
SISTEMA-NACI-NAL-DE-ALERTA-TEMPRANA-DE-INCENDIOS-FORESTALES/
├── app/                         # Backend FastAPI
│   ├── main.py                  # Endpoints: /risk/today, /predict, /firms/hotspots, /report/pdf…
│   ├── model.py                 # Modelo + umbrales operativos (classify) — fuente única de verdad
│   ├── security.py              # API key, CORS (lista blanca), rate-limit y validación de coordenadas
│   ├── pdf_generator.py         # Generador de reportes ejecutivos en PDF
│   ├── propagation.py           # Motor de simulación de propagación de fuego
│   ├── scheduler.py             # Scheduler de alertas diarias automáticas (07:00 Lima)
│   └── whatsapp_alerts.py       # Alertas a grupos de WhatsApp vía Green API
├── web/                         # Portal web ciudadano (Leaflet + HTML/CSS/JS)
│   ├── index.html               # Página principal del portal (AlertaForestal Perú)
│   ├── app.js                   # Lógica del mapa, FIRMS, formularios y métricas
│   └── styles.css               # Estilos del portal
├── data_pipeline/               # ETL y entrenamiento
│   ├── fetch_firms.py           # Descarga de focos térmicos (NASA FIRMS)
│   ├── fetch_era5.py            # Meteorología legacy (ERA5 vía Copernicus CDS)
│   ├── real_features.py         # Features reales SIN credenciales: DEM (Copernicus GLO-30), NDVI (Sentinel-2/AWS), OSM (Overpass), con caché
│   ├── grid_builder.py          # Grillas de ~1 km² (vecindario KNN), etiqueta honesta y panel multi-fecha
│   ├── refresh_dataset.py       # Recalcula features derivadas del dataset sin re-descargar (KNN + viento)
│   └── train_model.py           # Entrenamiento: Optuna + validación espacial OOF + umbrales data-driven
├── airflow/dags/                # DAGs para orquestación en Apache Airflow
├── dashboard/app.py             # Dashboard técnico en Streamlit + Folium
├── data/                        # dataset.parquet / dataset.csv + caché de features (data/cache/)
├── models/                      # lightgbm_wildfire.pkl + model_metadata.json (métricas y umbrales)
├── notebooks/model_evaluation.py# Comparación de modelos con validación espacial OOF
├── scripts/                     # Utilidades (generar_documento_codigo.py, health_check.py, envío de alertas…)
├── tests/                       # pytest (test_*.py) + auditorías ISO 25010 (audit_*.py) + test_lightgbm_precision.py
├── docs/                        # Memoria técnica del proyecto
├── CODIGO_COMPLETO_SISTEMA.txt  # Volcado de todo el código fuente del sistema
├── docker-compose.yml           # Contenedor de la API (con healthcheck y restart)
├── Dockerfile                   # Imagen Docker para la API
├── requirements.txt             # Dependencias de Python
├── requirements-dev.txt         # Dependencias de desarrollo/CI (pytest, ruff, httpx)
├── pyproject.toml               # Configuración de ruff / black / pytest
├── .github/workflows/ci.yml     # CI: lint (ruff) + pruebas (pytest)
├── .env.example                 # Plantilla de variables de entorno
└── README.md
```

---

## 🚀 Guía de Instalación y Uso

### 1. Clonar el Repositorio
```bash
git clone https://github.com/DanielMedina1727/SISTEMA-NACI-NAL-DE-ALERTA-TEMPRANA-DE-INCENDIOS-FORESTALES.git
cd SISTEMA-NACI-NAL-DE-ALERTA-TEMPRANA-DE-INCENDIOS-FORESTALES
```

### 2. Configurar Variables de Entorno
```bash
cp .env.example .env
```
Edita `.env` y completa las credenciales. **Todas son opcionales:** la API arranca y sirve el portal sin `.env` (solo se desactivan los servicios asociados).

> - **FIRMS_MAP_KEY** *(opcional)*: API Key gratuita en [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/). Habilita el proxy `/firms/hotspots` y la descarga de focos reales.
> - **GREEN_API_INSTANCE_ID**, **GREEN_API_TOKEN** *(alertas WhatsApp)*: WhatsApp vía [Green API](https://green-api.com/) (plan gratuito, sin Meta). Vincula tu número escaneando un QR.
> - **WHATSAPP_GROUP_IDS**: IDs de grupo/número separados por coma (formato `120363XXXXXXXX@g.us`), destino del resumen diario de las 07:00.
> - **CDS_API_KEY** *(legacy, opcional)*: solo lo usa `data_pipeline/fetch_era5.py`. La ingesta de features reales (`real_features.py`) usa **Open-Meteo** y **AWS** y **no requiere credenciales**.
> - **ADMIN_API_KEY** *(recomendado)*: si se define, los endpoints `POST /alert/whatsapp` y `POST /alert/daily` exigen la cabecera `X-API-Key`. Si se deja vacía, quedan sin protección (modo demo).
> - **ALLOWED_ORIGINS** *(opcional)*: lista blanca de CORS separada por comas. Por defecto solo se permiten orígenes locales (`:5050`, `:8501`).

### 3. Crear Entorno Virtual e Instalar Dependencias
```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt        # runtime
# pip install -r requirements-dev.txt  # + herramientas de desarrollo/CI (pytest, ruff)
```

### 4. (Opcional) Levantar la API con Docker
```bash
docker compose up -d
```
Levanta **solo el contenedor de la API** (con `healthcheck` y `restart`). El sistema no requiere PostGIS ni MinIO.

### 5. Iniciar la API y el Portal Ciudadano
```bash
# Recomendado usar python -m para evitar problemas de rutas (PATH)
python -m uvicorn app.main:app --reload --port 5050 --host 0.0.0.0
```
- **Portal ciudadano (se auto-redirige a /web/):** `http://localhost:5050`
- **Swagger UI (documentación API):** `http://localhost:5050/docs`

### 6. (Opcional) Iniciar Dashboard Técnico Streamlit
Asegúrate de haber instalado los requerimientos primero (`pip install -r requirements.txt`).
```bash
python -m streamlit run dashboard/app.py
```
Accede en: `http://localhost:8501`

---

## 📡 Endpoints de la API

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/` | Portal web ciudadano (index.html) |
| `GET` | `/health` | Estado del servicio y frescura de datos: `model_version`, `training_date` y `thresholds` (Rojo/Amarillo) |
| `GET` | `/risk/today` | GeoJSON con el índice de riesgo por grilla — área de Cajamarca (`limit`, por defecto 1200). Muestreo aleatorio uniforme (sin usar la etiqueta) e incluye `stats` con los conteos reales del territorio |
| `GET` | `/firms/hotspots` | Focos de calor reales de NASA FIRMS (proxy; la API key no se expone al frontend) |
| `POST` | `/predict` | Inferencia individual del modelo (devuelve `probabilidad`, `percentil` y `nivel`) |
| `POST` | `/propagate` | Simulación de propagación de fuego por viento |
| `POST` | `/alert/whatsapp` | Envía alerta de WhatsApp para grilla en nivel Rojo *(requiere `X-API-Key` si `ADMIN_API_KEY` está definida)* |
| `POST` | `/alert/daily` | Dispara manualmente el resumen diario a todos los grupos WhatsApp *(requiere `X-API-Key` si `ADMIN_API_KEY` está definida)* |
| `GET` | `/alert/status` | Estado del scheduler y próxima ejecución programada |
| `POST` | `/report/citizen` | Registra un reporte ciudadano de foco/humo (valida coordenadas en Perú y limita a 5 por IP cada 10 min) |
| `GET` | `/report/recent` | Últimos reportes ciudadanos registrados |
| `GET` | `/report/pdf` | Descarga el informe ejecutivo en PDF |
| `GET` | `/model/importance` | Importancia de características del modelo (SHAP) |
| `GET` | `/social/matrix` | Matriz de entorno social y mitigación de restricciones |

### Parámetros de `/firms/hotspots`

| Parámetro | Valores | Por defecto | Descripción |
|---|---|---|---|
| `region` | `peru`, `cajamarca`, `norte`, `sur`, `amazonia` | `peru` | Área geográfica |
| `source` | `VIIRS_SNPP_NRT`, `VIIRS_NOAA20_NRT`, `MODIS_NRT` | `VIIRS_SNPP_NRT` | Satélite/sensor |
| `days` | `1`–`7` | `1` | Últimos N días |

### Campos de entrada de `/predict`

Solo `grid_id` es obligatorio; el resto tiene valores por defecto. Las variables **temporales/espaciales son opcionales** (si se omiten, el modelo usa sus valores por defecto).

```json
{
  "grid_id": "CAJ-001",
  "pendiente_pct": 15.0,
  "orientacion": "NE",
  "ndvi": 0.45,
  "dist_carretera_m": 500.0,
  "dist_poblado_m": 1000.0,
  "temp_2m": 26.5,
  "humedad_relativa": 35.0,
  "viento_velocidad": 18.0,
  "viento_direccion": 45.0,

  "dias_sin_lluvia": 12.0,
  "lluvia_acum_7d": 15.0,
  "lluvia_acum_15d": 35.0,
  "temp_lag1": 22.0,
  "humedad_lag1": 45.0,
  "ndvi_anomaly": 0.0,
  "temp_vecindad_media": 22.0,
  "humedad_vecindad_media": 45.0
}
```

**Respuesta** (`PredictionResponse`):

```json
{ "grid_id": "CAJ-001", "probabilidad": 0.0319, "percentil": 81.0, "nivel": "Verde" }
```

> El **percentil** ubica el score frente a la distribución real del modelo (Top-1% ⇒ Rojo, Top-5% ⇒ Amarillo). Una entrada incompleta (sin `grid_id`) devuelve **HTTP 422**.

---

## 🚦 Semáforo y Umbrales de Riesgo

Los niveles **Verde / Amarillo / Rojo** se calculan con **presupuesto de alerta** (no con valores fijos arbitrarios):

| Nivel | Regla | Valor actual (aprox.) |
|---|---|---|
| 🔴 Rojo | Top-1 % de celdas por score del modelo (p99) | `0.132` |
| 🟡 Amarillo | Top-5 % de celdas por score (p95) | `0.098` |
| 🟢 Verde | Resto del territorio | `< 0.098` |

Los umbrales se recalculan en cada entrenamiento y se guardan en `models/model_metadata.json` (`serving_thresholds`). `app/model.py` expone `classify()` como **fuente única de verdad**, usada por `/predict`, `/risk/today`, el scheduler de WhatsApp y el dashboard. Son un **criterio de ranking relativo** (presupuesto de alerta), no una probabilidad absoluta calibrada.

---

## 🧪 Pruebas y Auditorías

Requieren la API corriendo en el puerto 5050:

```bash
python -m uvicorn app.main:app --port 5050
```

```bash
python tests/test_lightgbm_precision.py   # comportamiento del modelo (separación por ranking + latencia)
python tests/audit_quick.py               # resumen ejecutivo ISO 25010
python tests/audit_final.py               # auditoría extendida
python tests/iso25010_audit.py            # auditoría completa ISO/IEC 25010
```

**Último resultado:** `audit_quick` **85/85** · `audit_final` **106/106** · `iso25010` **133/133** · `test_lightgbm_precision` **APROBADO**.

### Pruebas automatizadas (pytest) y lint

No requieren la API en ejecución (usan `TestClient` en memoria):

```bash
pip install -r requirements-dev.txt

ruff check .          # lint (errores reales: imports/atributos indefinidos, código muerto)
pytest -q             # 32 pruebas: modelo, API, seguridad y pipeline
```

La CI (`.github/workflows/ci.yml`) ejecuta `ruff` y `pytest` en cada `push`/`pull request`.

### Pruebas de Carga

```bash
locust -f tests/locustfile.py --host=http://127.0.0.1:5050
```
Interfaz de Locust disponible en: `http://localhost:8089`

---

## 📄 Licencia

Este proyecto está bajo la **Licencia MIT** — uso libre y gratuito para comunidades, instituciones y desarrolladores.

Desarrollado por estudiantes de **Ingeniería de Sistemas Computacionales** de Perú. Datos: NASA FIRMS · ERA5 (Open-Meteo) · Copernicus DEM · Sentinel-2 · OpenStreetMap.
