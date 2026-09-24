# 🔥 Sistema Nacional de Alerta Temprana de Incendios Forestales — Perú

Portal ciudadano y API de predicción en tiempo real que clasifica zonas geográficas (grillas de 1 km²) en 3 niveles de riesgo (**Verde / Amarillo / Rojo**) con 24 horas de anticipación, integrando datos satelitales de NASA FIRMS (VIIRS), variables atmosféricas de Copernicus ERA5 y topografía USGS SRTM.

---

## 📌 Tabla de Contenidos
- [Descripción del Proyecto](#-descripción-del-proyecto)
- [Portal Web Ciudadano](#-portal-web-ciudadano)
- [Arquitectura y Funcionamiento](#-arquitectura-y-funcionamiento)
- [Stack Tecnológico](#-stack-tecnológico)
- [Estructura del Repositorio](#-estructura-del-repositorio)
- [Guía de Instalación y Uso](#-guía-de-instalación-y-uso)
- [Endpoints de la API](#-endpoints-de-la-api)
- [Pruebas de Carga](#-pruebas-de-carga)

---

## 🌲 Descripción del Proyecto

El **Sistema Nacional de Alerta Temprana de Incendios Forestales** es una solución integral para la prevención y alerta temprana de incendios forestales en Perú. El sistema:

- Procesa diariamente imágenes satelitales, datos meteorológicos y elevación del terreno para calcular probabilidades de riesgo por celda de 1 km².
- Expone un **portal web ciudadano** de acceso abierto con mapa interactivo en tiempo real.
- Consume focos VIIRS reales desde **NASA FIRMS** a través de un proxy FastAPI (sin problemas de CORS).
- Integra un motor de propagación del fuego simulado basado en pendiente y viento.
- Genera reportes ejecutivos automáticos en PDF y alertas en tiempo real por Telegram.

> **Estado de los datos en el portal:** El mapa distingue visualmente entre datos reales (API activa) y datos de referencia histórica (API offline). El popup de cada foco muestra `✅ Foco Satelital REAL` cuando los datos provienen de NASA FIRMS en tiempo real.

---

## 🗺️ Portal Web Ciudadano

El portal está disponible en `http://localhost:8000` (o `http://localhost:8000/web/`) al iniciar la API.

### Funcionalidades del portal

| Sección | Descripción |
|---|---|
| **Mapa en Vivo** | Grillas de riesgo IA + focos VIIRS reales de NASA FIRMS |
| **Mapa de Calor** | Capa heatmap de probabilidad de incendio |
| **Focos Satelitales** | Puntos VIIRS con confianza, FRP, satélite y hora de detección |
| **Alertas WhatsApp** | Suscripción por zona con QR y protocolo de difusión responsable |
| **Reportar Foco** | Formulario ciudadano con selección GPS o clic en mapa |
| **Centro de Recursos** | Guías de prevención, números de emergencia, condiciones meteorológicas |
| **Transparencia** | Fuentes de datos, métricas del modelo, declaración de interés público |

### Estados del mapa

- **Banner naranja** `⚠️ API offline`: La API no está activa; se muestran predicciones simuladas y coordenadas de referencia histórica.
- **Banner verde** `✅ Modelo LightGBM activo` *(se auto-oculta en 4s)*: API activa con datos reales del modelo.
- **Popup verde** `✅ Foco Satelital REAL`: Foco detectado por NASA FIRMS hoy.
- **Popup amarillo** `📋 Foco de Referencia Histórica`: Solo aparece cuando la API no está disponible.

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
   - **LightGBM**: Clasificador supervisado (Verde / Amarillo / Rojo). ROC-AUC: 0.9966, inferencia < 2 ms.
   - **Motor de Propagación**: Simulación de dirección y velocidad del fuego según viento y topografía (`SciPy`).

4. **API Backend (FastAPI)**
   - Proxy para NASA FIRMS sin restricciones CORS.
   - Endpoints de predicción, propagación, reportes PDF y alertas Telegram.

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
| **Alertas & Reportes** | Telegram Bot API, ReportLab | Notificaciones automáticas y PDF ejecutivo |
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
│   └── telegram_alerts.py       # Integración con Telegram Bot API
├── web/                         # Portal web ciudadano (Leaflet + HTML/CSS/JS)
│   ├── index.html               # Página principal del portal
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
> - **TELEGRAM_TOKEN** y **TELEGRAM_CHAT_ID**: Token obtenido vía [@BotFather](https://t.me/BotFather).

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
uvicorn app.main:app --reload --port 8000
```
- **Portal ciudadano:** `http://localhost:8000`
- **Swagger UI (documentación API):** `http://localhost:8000/docs`

### 6. (Opcional) Iniciar Dashboard Técnico Streamlit
```bash
streamlit run dashboard/app.py
```
Accede en: `http://localhost:8501`

---

## 📡 Endpoints de la API

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/` | Redirección al portal web ciudadano |
| `GET` | `/health` | Estado del servicio y modelo LightGBM |
| `GET` | `/risk/today` | GeoJSON con predicciones de riesgo por grilla (hoy) |
| `GET` | `/risk/{grid_id}` | Detalle de una grilla específica |
| `GET` | `/firms/hotspots` | Focos de calor reales de NASA FIRMS (proxy sin CORS) |
| `POST` | `/predict` | Inferencia individual del modelo LightGBM |
| `POST` | `/propagate` | Simulación de propagación de fuego por viento |
| `POST` | `/alert/telegram` | Envía alerta de Telegram para grilla en nivel Rojo |
| `GET` | `/report/pdf` | Descarga el informe ejecutivo en PDF |
| `GET` | `/model/importance` | Importancia de características del modelo LightGBM |
| `GET` | `/social/matrix` | Matriz de entorno social y mitigación de restricciones |

### Parámetros de `/firms/hotspots`

| Parámetro | Valores | Por defecto | Descripción |
|---|---|---|---|
| `region` | `peru`, `cajamarca`, `norte`, `sur`, `amazonia` | `peru` | Área geográfica |
| `source` | `VIIRS_SNPP_NRT`, `VIIRS_NOAA20_NRT`, `MODIS_NRT` | `VIIRS_SNPP_NRT` | Satélite/sensor |
| `days` | `1`–`7` | `1` | Últimos N días |

---

## 🧪 Pruebas de Carga

```bash
locust -f tests/locustfile.py --host=http://localhost:8000
```
Interfaz de Locust disponible en: `http://localhost:8089`

---

## 📄 Licencia

Este proyecto está bajo la **Licencia MIT** — uso libre y gratuito para comunidades, instituciones y desarrolladores.
