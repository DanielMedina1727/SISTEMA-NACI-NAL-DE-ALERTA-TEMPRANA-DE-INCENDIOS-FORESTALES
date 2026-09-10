# 🔥 Sistema de Predicción de Riesgo de Incendios Forestales

Arquitectura de datos en tiempo real para clasificar zonas geográficas (grillas de 1 km²) en 3 niveles de riesgo (**Verde** / **Amarillo** / **Rojo**) con 24 horas de anticipación, utilizando fusión de sensores remotos (NASA FIRMS), variables atmosféricas (Copernicus ERA5) y topografía (USGS SRTM).

---

## 📌 Tabla de Contenidos
- [Descripción del Proyecto](#-descripción-del-proyecto)
- [Arquitectura y Funcionamiento](#-arquitectura-y-funcionamiento)
- [Stack Tecnológico](#-stack-tecnológico)
- [Herramientas y Programas Necesarios](#-herramientas-y-programas-necesarios)
- [Estructura del Repositorio](#-estructura-del-repositorio)
- [Guía de Instalación y Uso](#-guía-de-instalación-y-uso)
- [Pruebas de Carga](#-pruebas-de-carga)

---

## 🌲 Descripción del Proyecto

El **Sistema de Predicción de Riesgo de Incendios Forestales** es una solución integral orientada a la prevención y alerta temprana de incendios. El sistema procesa diariamente imágenes satelitales, datos meteorológicos y elevación del terreno para calcular probabilidades de riesgo por celdas geográficas de 1 km x 1 km. 

Además de la clasificación de riesgo, integra un motor de propagación del fuego simulado basado en la pendiente del terreno y el viento, generación automática de reportes ejecutivos en PDF y alertas en tiempo real mediante un bot de Telegram.

---

## ⚙️ Arquitectura y Funcionamiento

El flujo de trabajo del proyecto se compone de 5 módulos o etapas principales:

1. **Ingesta y Orquestación de Datos (ETL)**:
   - **NASA FIRMS**: Descarga de datos de focos de calor/anomalías térmicas satelitales en tiempo real e históricos.
   - **Copernicus ERA5**: Extracción de variables meteorológicas (temperatura, humedad relativa, velocidad y dirección del viento).
   - **USGS SRTM**: Obtención de datos de elevación y pendiente del terreno.
   - **Apache Airflow**: DAGs programados para la ejecución periódica y automatizada del flujo de ingesta.

2. **Almacenamiento Geoespacial**:
   - **PostGIS (PostgreSQL)**: Almacenamiento relacional espacial para grillas, geometrías vectoriales e índices espaciales (`ST_Contains`, `ST_Buffer`).
   - **MinIO**: Almacenamiento de objetos (S3-compatible) para rásters pesados y archivos GeoTIFF.

3. **Machine Learning y Simulación**:
   - **LightGBM**: Modelo supervisado clasificador entrenado con datos históricos desbalanceados para clasificar cada celda en riesgo Bajo (Verde), Moderado (Amarillo) o Alto (Rojo).
   - **Motor de Propagación**: Algoritmo computacional (`SciPy`) que simula la dirección y velocidad de propagación del fuego según las condiciones locales de viento y topografía.

4. **API Backend y Servicios (FastAPI)**:
   - Expone endpoints REST (`/predict`, `/grid/{id}`, `/health`) para consultar el nivel de riesgo por ubicación o zona.
   - Módulo de generación de reportes en PDF y servicio de alertas integradas con Telegram.

5. **Visualización y Monitoreo**:
   - **Streamlit + Folium**: Dashboard interactivo con mapas temáticos, visualización de grillas coloreadas según el nivel de riesgo y herramientas de análisis.
   - **Locust**: Suite de pruebas de rendimiento para simular consumo masivo y concurrente de la API REST.

---

## 🛠️ Stack Tecnológico

| Capa | Herramienta / Librería | Función Principal |
|---|---|---|
| **Orquestación ETL** | Apache Airflow | Automatización y programación de pipelines de datos |
| **Bases de Datos** | PostGIS / PostgreSQL | Almacenamiento espacial y consultas relacionales |
| **Almacenamiento Ráster** | MinIO (S3 Compatible) | Almacenamiento de objetos para GeoTIFFs y archivos pesados |
| **Machine Learning** | LightGBM, Scikit-Learn | Clasificación del nivel de riesgo e inferencia |
| **Procesamiento Espacial** | GeoPandas, Shapely, Rasterio | Manipulación de vectores y datos ráster |
| **Backend API** | FastAPI, Uvicorn | Servicio API REST de alto rendimiento |
| **Frontend / Dashboard** | Streamlit, Folium, Plotly | Dashboard interactivo y mapas temáticos |
| **Alertas & Reportes** | Telegram Bot API | Notificaciones de alerta automatizadas |
| **Pruebas de Carga** | Locust | Evaluación de rendimiento y concurrencia |
| **Despliegue** | Docker & Docker Compose | Contenedorización de la infraestructura |

---

## 💻 Herramientas y Programas Necesarios

Para trabajar con este proyecto se requiere/recomienda la instalación de los siguientes programas:

1. **Python 3.11+**: Lenguaje base para los pipelines, la API, el modelo y el dashboard.
2. **Docker Desktop**: Necesario para desplegar los contenedores de PostGIS, MinIO y los servicios del sistema mediante `docker compose`.
3. **VS Code** o **Cursor**: Editor de código recomendado para el desarrollo.
4. **DBeaver** o **pgAdmin**: Clientes visuales de base de datos para inspeccionar tablas espacialmente en PostGIS.
5. **QGIS**: Sistema de Información Geográfica (SIG/GIS) imprescindible para inspeccionar archivos ráster (GeoTIFFs), verificar las grillas de 1km² y validar geometrías antes de cargarlas al pipeline.
6. **Postman** o **Insomnia**: Para realizar pruebas manuales a los endpoints de la API FastAPI.
7. **Git / GitHub Desktop**: Para el control de versiones y sincronización del repositorio.

---

## 📂 Estructura del Repositorio

```
wildfire-project/
├── app/                    # Backend en FastAPI
│   ├── main.py              # Endpoints principales (/predict, /grid/{id}, /health)
│   ├── model.py              # Carga y ejecución del modelo LightGBM
│   ├── pdf_generator.py      # Generador de reportes ejecutivos en PDF
│   ├── propagation.py        # Motor de simulación de propagación de fuego
│   └── telegram_alerts.py    # Integración de alertas con Telegram Bot API
├── data_pipeline/           # Scripts de Ingesta y ETL
│   ├── fetch_firms.py         # Descarga de focos térmicos (NASA FIRMS)
│   ├── fetch_era5.py          # Extracción meteorológica (Copernicus ERA5)
│   ├── fetch_srtm.py          # Extracción topográfica (USGS SRTM)
│   ├── grid_builder.py        # Generador de grillas de 1km² e integración de datos
│   └── train_model.py         # Pipeline de entrenamiento del modelo ML
├── airflow/
│   └── dags/                  # DAGs para orquestación en Apache Airflow
├── dashboard/
│   └── app.py                 # Dashboard interactivo en Streamlit y Folium
├── notebooks/                # Exploración de datos y prototipado
├── tests/
│   └── locustfile.py          # Pruebas de carga con Locust
├── docker-compose.yml         # Infraestructura (PostGIS, MinIO, API)
├── requirements.txt           # Dependencias de Python
└── .env.example               # Plantilla de variables de entorno
```

---

## 🚀 Guía de Instalación y Uso

### 1. Clonar el Repositorio
```bash
git clone https://github.com/tu-usuario/wildfire-project.git
cd wildfire-project
```

### 2. Configurar Variables de Entorno
Copia el archivo de ejemplo `.env.example` a `.env` y completa tus claves de API:
```bash
cp .env.example .env
```
> **Credenciales sugeridas / requeridas:**
> - **NASA FIRMS API Key**: Gratuita en [NASA FIRMS API](https://firms.modaps.eosdis.nasa.gov/api/).
> - **Copernicus CDS (ERA5)**: Registro gratuito en [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/).
> - **Telegram Bot**: Token obtenido mediante [@BotFather](https://t.me/BotFather) en Telegram.

### 3. Levantar Infraestructura con Docker
```bash
docker compose up -d
```

### 4. Entorno de Python e Ingesta de Datos
Crea un entorno virtual e instala las dependencias:
```bash
python -m venv venv

# En Windows:
venv\Scripts\activate

# En Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

Ejecuta la ingesta de datos inicial:
```bash
python data_pipeline/fetch_firms.py --country PER --days 30
```

### 5. Iniciar la API Backend y el Dashboard
- **Iniciar API FastAPI:**
  ```bash
  uvicorn app.main:app --reload --port 8000
  ```
  Swagger UI disponible en: `http://localhost:8000/docs`

- **Iniciar Dashboard Streamlit:**
  ```bash
  streamlit run dashboard/app.py
  ```
  Accede al dashboard en: `http://localhost:8501`

---

## 🧪 Pruebas de Carga
Para realizar pruebas de rendimiento sobre la API:
```bash
locust -f tests/locustfile.py --host=http://localhost:8000
```
Abre la interfaz de Locust en `http://localhost:8089`.

---

## 📄 Licencia
Este proyecto está bajo la Licencia MIT.

