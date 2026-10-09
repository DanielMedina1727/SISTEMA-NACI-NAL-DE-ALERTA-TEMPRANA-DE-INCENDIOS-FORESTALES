# 🔥 AlertaForestal Perú — Sistema Nacional de Alerta Temprana de Incendios Forestales

Portal ciudadano y API de predicción en tiempo real que clasifica zonas geográficas (grillas de ~1 km²) en 3 niveles de riesgo (**Verde / Amarillo / Rojo**) con 24 horas de anticipación, integrando datos satelitales de NASA FIRMS (VIIRS), variables atmosféricas de Copernicus ERA5 y topografía USGS SRTM.

---

## 📌 Tabla de Contenidos
- [Descripción del Proyecto](#-descripción-del-proyecto)
- [Portal Web Ciudadano](#%EF%B8%8F-portal-web-ciudadano)
- [Arquitectura y Funcionamiento](#%EF%B8%8F-arquitectura-y-funcionamiento)
- [Stack Tecnológico](#%EF%B8%8F-stack-tecnológico)
- [Estructura del Repositorio](#-estructura-del-repositorio)
- [Guía de Instalación y Uso](#-guía-de-instalación-y-uso)
- [Endpoints de la API](#-endpoints-de-la-api)
- [Pruebas de Carga](#-pruebas-de-carga)

---

## 🌲 Descripción del Proyecto

**AlertaForestal Perú** es una plataforma ciudadana y comunitaria de monitoreo, prevención y alerta temprana de incendios forestales en tiempo real. El sistema:

- Procesa diariamente imágenes satelitales, datos meteorológicos y elevación del terreno para calcular probabilidades de riesgo por celda de ~1 km².
- Expone un **portal web ciudadano** de acceso abierto con mapa interactivo en tiempo real.
- Consume focos VIIRS reales desde **NASA FIRMS** a través de un proxy FastAPI (sin problemas de CORS).
- Integra un motor de propagación del fuego simulado basado en pendiente y viento.
- Genera reportes ejecutivos automáticos en PDF y alertas en tiempo real por WhatsApp.
- Envía un **resumen diario automático** a todos los grupos comunitarios de WhatsApp a las 07:00 (Lima, UTC-5).

> **Estado de los datos en el portal:** El mapa distingue visualmente entre datos reales (API activa) y datos de referencia histórica (API offline). El popup de cada foco muestra `✅ Foco Satelital REAL` cuando los datos provienen de NASA FIRMS en tiempo real.

---

## 🗺️ Portal Web Ciudadano

El portal está disponible en **`http://localhost:5050`** al iniciar la API.

| Sección | Tag | Descripción |
|---|---|---|
| **Hero / Inicio** | `#hero` | Indicador de riesgo en tiempo real, métricas del día y accesos directos |
| **Mapa en Vivo** | `#mapa` | Grillas de riesgo IA + focos VIIRS reales de NASA FIRMS con filtros de región y horizonte temporal |
| **Alertas WhatsApp** | `#whatsapp` | Suscripción por zona/provincia con QR, flujo de información y protocolo de difusión responsable |
| **Reportar Foco** | `#reporte` | Formulario ciudadano con selección GPS, clic en mapa mini-interactivo y carga de fotos |
| **Centro de Recursos** | `#recursos` | Guías de prevención, widget meteorológico FWI en vivo y directorio de emergencias |
| **Transparencia** | `#transparencia` | Fuentes de datos, métricas del modelo LightGBM y declaración de interés público |

### Métricas en tiempo real (Hero)

| Métrica | Descripción |
|---|---|
| 🛰️ **Focos VIIRS Reales** | Focos de calor activos detectados por satélite hoy |
| 🔴 **Zonas Alto Riesgo** | Grillas con probabilidad ≥ 70% |
| 🟡 **Vigilancia** | Grillas con probabilidad entre 35–69% |
| 📊 **Zonas Monitoreadas** | Total de grillas analizadas |
| ⏱ **Anticipación IA** | 24 horas de anticipación con LightGBM |

### Capas del Mapa Interactivo

- 🌡️ **Mapa de Calor** — Heatmap de probabilidad de incendio
- 🟥 **Zonas IA** — Grillas coloreadas por nivel de riesgo (Rojo / Naranja / Verde)
- 🛰️ **Focos Reales VIIRS** — Puntos satelitales de NASA FIRMS con confianza, FRP, satélite y hora

### Simbología

| Color | Umbral | Significado |
|---|---|---|
| 🔴 Rojo | ≥ 70% | Foco activo — acción inmediata |
| 🟠 Naranja | 35–69% | Bajo observación — vigilancia activa |
| 🟢 Verde | < 35% | Zona controlada |
| 📍 Punto | — | Foco VIIRS real detectado vía NASA FIRMS |

### Estados del mapa

- **Banner naranja** `⚠️ API offline`: La API no está activa; se muestran predicciones simuladas y coordenadas de referencia histórica.
- **Banner verde** `✅ Modelo LightGBM activo` *(se auto-oculta en 4s)*: API activa con datos reales del modelo.
- **Popup verde** `✅ Foco Satelital REAL`: Foco detectado por NASA FIRMS hoy.
- **Popup amarillo** `📋 Foco de Referencia Histórica`: Solo aparece cuando la API no está disponible.

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
   - **NASA FIRMS**: Focos de calor VIIRS/MODIS satelitales en tiempo real.
   - **Copernicus ERA5**: Variables meteorológicas (temperatura, humedad, viento).
   - **USGS SRTM**: Elevación y pendiente del terreno a 30 m de resolución.
   - **Apache Airflow**: DAGs para ejecución periódica y automatizada.

2. **Almacenamiento Geoespacial**
   - **PostGIS (PostgreSQL)**: Grillas vectoriales e índices espaciales.
   - **MinIO**: Almacenamiento S3-compatible para archivos GeoTIFF y rásters.

3. **Machine Learning y Simulación**
   - **LightGBM**: Clasificador supervisado (Verde / Amarillo / Rojo). ROC-AUC: 0.9966, detección de focos reales: 97.85%, inferencia < 2 ms.
   - **Motor de Propagación**: Simulación de dirección y velocidad del fuego según viento y topografía (`SciPy`).

4. **API Backend (FastAPI)**
   - Proxy para NASA FIRMS sin restricciones CORS.
   - Endpoints de predicción, propagación, reportes PDF y alertas WhatsApp.
   - Scheduler automático de alertas diarias a todos los grupos comunitarios.

5. **Portal Web y Visualización**
   - Frontend HTML/CSS/JS con Leaflet para el mapa interactivo.
   - Dashboard Streamlit con Folium y Plotly.

---

## 🛠️ Stack Tecnológico

| Capa | Herramienta / Librería | Función Principal |
|---|---|---|
| **Orquestación ETL** | Apache Airflow | Automatización y programación de pipelines |
| **Bases de Datos** | PostGIS / PostgreSQL | Almacenamiento espacial y consultas relacionales |
| **Almacenamiento Ráster** | MinIO (S3 Compatible) | GeoTIFFs y archivos pesados |
| **Machine Learning** | LightGBM, Scikit-Learn | Clasificación de riesgo e inferencia |
| **Procesamiento Espacial** | GeoPandas, Shapely, Rasterio | Vectores y datos ráster |
| **Backend API** | FastAPI, Uvicorn | API REST de alto rendimiento |
| **Portal Web** | HTML5, CSS3, JavaScript, Leaflet | Portal ciudadano de acceso abierto |
| **Dashboard Interno** | Streamlit, Folium, Plotly | Dashboard técnico interactivo |
| **Datos Satelitales** | NASA FIRMS (VIIRS/MODIS) | Focos de calor en tiempo real |
| **Alertas & Reportes** | WhatsApp Business API (Meta), ReportLab | Notificaciones automáticas y PDF ejecutivo |
| **Pruebas de Carga** | Locust | Evaluación de rendimiento y concurrencia |
| **Despliegue** | Docker & Docker Compose | Contenedorización de la infraestructura |

---

## 💻 Herramientas y Programas Necesarios

1. **Python 3.11+**: Lenguaje base para pipelines, API, modelo y dashboard.
2. **Docker Desktop**: Para contenedores de PostGIS, MinIO y servicios del sistema.
3. **VS Code** o **Cursor**: Editor de código recomendado.
4. **DBeaver** o **pgAdmin**: Clientes para inspeccionar tablas espaciales en PostGIS.
5. **QGIS**: SIG para inspeccionar GeoTIFFs y grillas de 1 km².
6. **Postman** o **Insomnia**: Para pruebas manuales de endpoints FastAPI.
7. **Git / GitHub Desktop**: Control de versiones y sincronización.

---

## 📂 Estructura del Repositorio

```
SISTEMA-NACI-NAL-DE-ALERTA-TEMPRANA-DE-INCENDIOS-FORESTALES/
├── app/                         # Backend FastAPI
│   ├── main.py                  # Endpoints: /risk/today, /firms/hotspots, /predict, /report/pdf…
│   ├── model.py                 # Carga y ejecución del modelo LightGBM
│   ├── pdf_generator.py         # Generador de reportes ejecutivos en PDF
│   ├── propagation.py           # Motor de simulación de propagación de fuego
│   ├── scheduler.py             # Scheduler de alertas diarias automáticas (07:00 Lima)
│   └── whatsapp_alerts.py       # Integración con WhatsApp Business Cloud API (Meta)
├── web/                         # Portal web ciudadano (Leaflet + HTML/CSS/JS)
│   ├── index.html               # Página principal del portal (AlertaForestal Perú)
│   ├── app.js                   # Lógica del mapa, FIRMS, formularios y métricas
│   └── styles.css               # Estilos del portal
├── data_pipeline/               # Scripts ETL de ingesta de datos
│   ├── fetch_firms.py           # Descarga de focos térmicos (NASA FIRMS)
│   ├── fetch_era5.py            # Extracción meteorológica (Copernicus ERA5)
│   ├── fetch_srtm.py            # Extracción topográfica (USGS SRTM)
│   ├── grid_builder.py          # Generador de grillas de 1 km² e integración de datos
│   └── train_model.py           # Pipeline de entrenamiento del modelo ML
├── airflow/
│   └── dags/                    # DAGs para orquestación en Apache Airflow
├── dashboard/
│   └── app.py                   # Dashboard técnico en Streamlit y Folium
├── data/                        # Datasets procesados (dataset.parquet / .csv)
├── models/                      # Modelos entrenados (.pkl / .lgb)
├── notebooks/                   # Exploración de datos y prototipado
├── tests/
│   └── locustfile.py            # Pruebas de carga con Locust
├── docker-compose.yml           # Infraestructura (PostGIS, MinIO, API)
├── Dockerfile                   # Imagen Docker para la API
├── requirements.txt             # Dependencias de Python
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
Edita `.env` y completa las credenciales:

> - **FIRMS_MAP_KEY**: API Key gratuita en [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/).
> - **CDS_API_KEY**: Registro gratuito en [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/).
> - **WHATSAPP_TOKEN**: Token de acceso de la app Meta. Obténlo en [Meta for Developers](https://developers.facebook.com/apps/).
> - **WHATSAPP_PHONE_NUMBER_ID**: ID del número de teléfono empresarial en WhatsApp Business.
> - **WHATSAPP_RECIPIENT_NUMBER**: Número de destino con código de país (ej. `51987654321`).

### 3. Crear Entorno Virtual e Instalar Dependencias
```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 4. (Opcional) Levantar Infraestructura con Docker
```bash
docker compose up -d
```

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
| `GET` | `/health` | Estado del servicio y modelo LightGBM |
| `GET` | `/risk/today` | GeoJSON con predicciones de riesgo por grilla (hoy) — área de Cajamarca |
| `GET` | `/risk/{grid_id}` | Detalle de una grilla específica |
| `GET` | `/firms/hotspots` | Focos de calor reales de NASA FIRMS (proxy sin CORS) |
| `POST` | `/predict` | Inferencia individual del modelo LightGBM |
| `POST` | `/propagate` | Simulación de propagación de fuego por viento |
| `POST` | `/alert/whatsapp` | Envía alerta de WhatsApp para grilla en nivel Rojo |
| `POST` | `/alert/daily` | Dispara manualmente el resumen diario a todos los grupos WhatsApp |
| `GET` | `/alert/status` | Estado del scheduler y próxima ejecución programada |
| `GET` | `/report/pdf` | Descarga el informe ejecutivo en PDF |
| `GET` | `/model/importance` | Importancia de características del modelo LightGBM |
| `GET` | `/social/matrix` | Matriz de entorno social y mitigación de restricciones |

### Parámetros de `/firms/hotspots`

| Parámetro | Valores | Por defecto | Descripción |
|---|---|---|---|
| `region` | `peru`, `cajamarca`, `norte`, `sur`, `amazonia` | `peru` | Área geográfica |
| `source` | `VIIRS_SNPP_NRT`, `VIIRS_NOAA20_NRT`, `MODIS_NRT` | `VIIRS_SNPP_NRT` | Satélite/sensor |
| `days` | `1`–`7` | `1` | Últimos N días |

### Campos de entrada de `/predict`

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
  "viento_direccion": 45.0
}
```

---

## 🧪 Pruebas de Carga

```bash
locust -f tests/locustfile.py --host=http://localhost:5050
```
Interfaz de Locust disponible en: `http://localhost:8089`

---

## 📄 Licencia

Este proyecto está bajo la **Licencia MIT** — uso libre y gratuito para comunidades, instituciones y desarrolladores.

Desarrollado por estudiantes de **Ingeniería de Sistemas Computacionales** de Perú. Datos: NASA FIRMS · Copernicus ERA5 · USGS SRTM.
