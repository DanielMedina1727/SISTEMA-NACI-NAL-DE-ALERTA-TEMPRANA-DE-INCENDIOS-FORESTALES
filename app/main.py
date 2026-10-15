"""
API principal de predicción de riesgo de incendios forestales.
Expone:
  GET  /                    -> portal web ciudadano (redirige a /web/)
  GET  /health              -> estado del servicio y modelo
  GET  /risk/today          -> GeoJSON con el riesgo de hoy por grilla (Verde/Amarillo/Rojo)
  GET  /firms/hotspots      -> focos de calor reales de NASA FIRMS (proxy sin CORS)
  POST /predict             -> inferencia individual del modelo (probabilidad, percentil, nivel)
  POST /propagate           -> motor de propagación espacial por viento
  POST /alert/whatsapp      -> dispara alerta de WhatsApp para grilla Roja
  POST /alert/daily         -> dispara manualmente el resumen diario a todos los grupos
  GET  /alert/status        -> muestra el estado del scheduler y próxima ejecución
  GET  /report/pdf          -> informe ejecutivo en PDF
  GET  /model/importance    -> importancia de características del modelo (SHAP)
  GET  /social/matrix       -> matriz de entorno social y mitigación de restricciones
"""
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.model import RiskModel, classify, score_percentile
from app.propagation import propagate_risk
from app.whatsapp_alerts import send_red_alert
from app.scheduler import init_scheduler, run_daily_alerts

app = FastAPI(
    title="AlertaForestal Perú — API Pública",
    description=(
        "API de acceso abierto para el Sistema Nacional de Alerta Temprana de Incendios Forestales. "
        "Proporciona datos satelitales, predicciones de riesgo y motor de propagación. "
        "Portal ciudadano en /web/ · Swagger UI en /docs"
    ),
    version="2.0.0",
)

# CORS abierto para que el portal web pueda consumir la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Montar el portal web público en /web
_WEB_DIR = Path(__file__).parent.parent / "web"
if _WEB_DIR.exists():
    app.mount("/web", StaticFiles(directory=str(_WEB_DIR), html=True), name="portal-web")

# Inicializar el scheduler de alertas automáticas (07:00 Lima todos los días)
_scheduler = init_scheduler(app)

from fastapi.responses import RedirectResponse

@app.get("/", include_in_schema=False)
def root():
    """Redirige a la página principal del portal ciudadano."""
    return RedirectResponse(url="/web/")

model = RiskModel()
DATASET_PATH = Path(__file__).parent.parent / "data" / "dataset.parquet"


class GridFeatures(BaseModel):
    grid_id: str
    pendiente_pct: float = 15.0
    orientacion: str = "NE"
    ndvi: float = 0.45
    dist_carretera_m: float = 500.0
    dist_poblado_m: float = 1000.0
    temp_2m: float = 26.5
    humedad_relativa: float = 35.0
    viento_velocidad: float = 18.0
    viento_direccion: float = 45.0  # grados, 0 = Norte
    # Contexto temporal/espacial OPCIONAL: si no se envía, el modelo usa sus
    # valores por defecto (app.model.DEFAULT_VALUES).
    dias_sin_lluvia: Optional[float] = None
    lluvia_acum_7d: Optional[float] = None
    lluvia_acum_15d: Optional[float] = None
    temp_lag1: Optional[float] = None
    humedad_lag1: Optional[float] = None
    ndvi_anomaly: Optional[float] = None
    temp_vecindad_media: Optional[float] = None
    humedad_vecindad_media: Optional[float] = None


class PredictionResponse(BaseModel):
    grid_id: str
    probabilidad: float
    percentil: Optional[float] = None  # ubicación del score en la distribución del modelo
    nivel: str  # "Verde" | "Amarillo" | "Rojo"


class WhatsAppAlertRequest(BaseModel):
    grid_id: str
    lat: float
    lon: float
    confianza: float = 0.85


@app.get("/health")
def health():
    model_loaded = True
    try:
        _ = model.model
    except Exception:
        model_loaded = False

    return {
        "status": "ok",
        "service": "Wildfire Risk API",
        "model_loaded": model_loaded,
        "dataset_available": DATASET_PATH.exists(),
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(features: GridFeatures):
    try:
        # Pydantic v2: model_dump() (dict() está deprecado en v2).
        # Se descartan los campos opcionales no enviados para que el modelo use
        # sus DEFAULT_VALUES en las features temporales.
        payload = {k: v for k, v in features.model_dump().items() if v is not None}
        proba = model.predict_proba(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    nivel = classify(proba)
    return PredictionResponse(
        grid_id=features.grid_id,
        probabilidad=round(proba, 4),
        percentil=score_percentile(proba),
        nivel=nivel,
    )


@app.get("/risk/today")
def risk_today(limit: int = Query(default=1200, le=5000)):
    """
    Retorna las predicciones de riesgo de hoy por grilla en formato GeoJSON FeatureCollection,
    cubriendo el área espacial 2D de la provincia y departamento de Cajamarca.
    """
    csv_path = DATASET_PATH.with_suffix(".csv")
    if not csv_path.exists() and not DATASET_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Dataset no encontrado. Ejecuta data_pipeline/grid_builder.py primero."
        )

    if csv_path.exists():
        df_full = pd.read_csv(csv_path)
    else:
        df_full = pd.read_parquet(DATASET_PATH).drop(columns=["geometry"], errors="ignore")

    # Filtrar espacialmente para cubrir el área 2D de la región de Cajamarca (-7.7592 a -4.5519 Lat, -79.4517 a -77.7389 Lon)
    cajamarca_area = df_full[
        (df_full["latitude"] >= -7.7592) & (df_full["latitude"] <= -4.5519) &
        (df_full["longitude"] >= -79.4517) & (df_full["longitude"] <= -77.7389)
    ]

    if not cajamarca_area.empty:
        if len(cajamarca_area) > limit:
            # Seleccionar focos prioritarios y distribuir el resto uniformemente en todo el departamento
            high_risk = cajamarca_area[cajamarca_area["target"] == 1]
            n_high = min(len(high_risk), int(limit * 0.40))
            high_sample = high_risk.head(n_high)

            remaining_limit = limit - len(high_sample)
            other_rows = cajamarca_area.drop(high_sample.index, errors="ignore")
            step = max(1, len(other_rows) // remaining_limit)
            spatial_sample = other_rows.iloc[::step].head(remaining_limit)

            df = pd.concat([high_sample, spatial_sample]).reset_index(drop=True)
        else:
            df = cajamarca_area
    else:
        df = df_full.head(limit)

    # Inferencia en lote con el pipeline avanzado
    from app.model import FEATURE_ORDER
    for col in FEATURE_ORDER:
        if col not in df.columns:
            df[col] = 0.0

    try:
        probas = model.model.predict_proba(df[FEATURE_ORDER])[:, 1]
    except Exception:
        probas = [0.1] * len(df)


    features = []
    cell_size = 0.015

    for i, (idx, row) in enumerate(df.iterrows()):
        proba = float(probas[i])
        nivel = classify(proba)

        
        lon, lat = float(row["longitude"]), float(row["latitude"])
        poly_coords = [
            [lon - cell_size/2, lat - cell_size/2],
            [lon + cell_size/2, lat - cell_size/2],
            [lon + cell_size/2, lat + cell_size/2],
            [lon - cell_size/2, lat + cell_size/2],
            [lon - cell_size/2, lat - cell_size/2],
        ]

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [poly_coords],
            },
            "properties": {
                "grid_id": str(row["grid_id"]),
                "probabilidad": round(proba, 4),
                "nivel": nivel,
                "temp_2m": float(row.get("temp_2m", 25.0)),
                "humedad_relativa": float(row.get("humedad_relativa", 40.0)),
                "viento_velocidad": float(row.get("viento_velocidad", 15.0)),
                "viento_direccion": float(row.get("viento_direccion", 45.0)),
                "pendiente_pct": float(row.get("pendiente_pct", 10.0)),
                "ndvi": float(row.get("ndvi", 0.4)),
            }
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "count": len(features),
        "features": features,
    }


@app.post("/propagate")
def propagate(grid_id: str, viento_direccion: float = 45.0, viento_velocidad: float = 20.0):
    """Aplica el motor de propagación por viento a una grilla en Rojo."""
    return propagate_risk(grid_id, viento_direccion, viento_velocidad)


@app.post("/alert/whatsapp")
def trigger_alert(alert_req: WhatsAppAlertRequest):
    """Dispara alerta de WhatsApp a los bomberos/brigadas."""
    try:
        res = send_red_alert(
            grid_id=alert_req.grid_id,
            lat=alert_req.lat,
            lon=alert_req.lon,
            confianza=alert_req.confianza,
        )
        return {"status": "alerta_enviada", "whatsapp_response": res}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error enviando alerta WhatsApp: {exc}")


@app.post("/alert/daily", tags=["Alertas"])
async def trigger_daily_alerts():
    """
    Dispara manualmente el resumen diario de riesgo a todos los grupos de WhatsApp.
    Útil para pruebas o cuando se quiere enviar un boletín fuera del horario programado.
    """
    try:
        await run_daily_alerts()
        return {"status": "ok", "mensaje": "Alertas diarias enviadas a todos los grupos."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error en el envío de alertas: {exc}")


@app.get("/alert/status", tags=["Alertas"])
def get_alert_status():
    """
    Consulta el estado del scheduler de alertas automáticas.
    Muestra la próxima ejecución programada y el estado de cada job.
    """
    jobs = []
    for job in _scheduler.get_jobs():
        next_run = job.next_run_time.isoformat() if job.next_run_time else "no programado"
        jobs.append({
            "id":       job.id,
            "nombre":   job.name,
            "proxima_ejecucion": next_run,
            "activo":   job.next_run_time is not None,
        })
    return {
        "scheduler_activo": _scheduler.running,
        "zona_horaria":    "America/Lima (UTC-5)",
        "horario":         "07:00 todos los días",
        "jobs":            jobs,
    }


@app.get("/report/pdf")
def get_executive_pdf_report():
    """Genera y descarga el informe ejecutivo oficial en formato PDF."""
    from fastapi.responses import Response
    from app.pdf_generator import generate_executive_pdf

    # Obtener riesgo actual
    risk_geojson = risk_today(limit=2000)
    features_list = risk_geojson.get("features", [])

    total = len(features_list)
    red_features = [f for f in features_list if f["properties"]["nivel"] == "Rojo"]
    yellow_features = [f for f in features_list if f["properties"]["nivel"] == "Amarillo"]
    green_features = [f for f in features_list if f["properties"]["nivel"] == "Verde"]

    risk_data = {
        "count": total,
        "red_count": len(red_features),
        "yellow_count": len(yellow_features),
        "green_count": len(green_features),
        "red_features": red_features,
    }

    pdf_bytes = generate_executive_pdf(risk_data)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=Informe_Ejecutivo_Incendios_Cajamarca.pdf"}
    )


@app.get("/model/importance")
def get_model_feature_importance():
    """Retorna la importancia de características del ensemble para interpretabilidad del modelo."""
    import json

    from app.model import FEATURE_ORDER

    # El modelo puede ser un VotingClassifier(LGB, XGB, RF) o estar envuelto en un
    # CalibratedClassifierCV. Ninguno de los dos expone `feature_importances_` a nivel
    # raíz, así que localizamos el LightGBM interno en cualquiera de las dos estructuras.
    importances = None
    try:
        _obj = model.model
        _ensemble = _obj.calibrated_classifiers_[0].estimator if hasattr(_obj, "calibrated_classifiers_") else _obj
        _first = _ensemble.estimators_[0]
        _lgb = _first[1] if isinstance(_first, tuple) else _first  # sklearn<1.5 usa tuplas
        _imp = list(_lgb.feature_importances_)
        if len(_imp) == len(FEATURE_ORDER):
            importances = _imp
    except Exception:
        importances = None

    if importances is not None:
        total = sum(importances) or 1.0
        result = [
            {"feature": name, "importance": round(val / total, 4), "percentage": round(val / total * 100, 2)}
            for name, val in zip(FEATURE_ORDER, importances)
        ]
        source = "lightgbm.feature_importances_"
    else:
        # Fallback robusto: importancias SHAP registradas en los metadatos MLOps
        meta_path = Path(__file__).parent.parent / "models" / "model_metadata.json"
        try:
            with open(meta_path, "r", encoding="utf-8") as fh:
                meta = json.load(fh)
            shap_imp = meta.get("shap_feature_importance", {})
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"No se pudo obtener la importancia de características: {exc}",
            )
        total = sum(shap_imp.values()) or 1.0
        result = [
            {"feature": k, "importance": round(v / total, 4), "percentage": round(v / total * 100, 2)}
            for k, v in shap_imp.items()
        ]
        source = "model_metadata.shap_feature_importance"

    result.sort(key=lambda x: x["importance"], reverse=True)
    return {
        "model": "Ensemble (LightGBM + XGBoost + RandomForest)",
        "n_features": len(FEATURE_ORDER),
        "importance_source": source,
        "feature_importance": result,
        "justification_vs_nn": "Se eligió el ensemble de árboles (LightGBM/XGBoost/RandomForest) sobre redes neuronales profundas (CNN/LSTM) debido a su mayor interpretabilidad (valores SHAP), menor costo computacional (inferencia < 2ms) y rendimiento superior en datos tabulares espacio-temporales discretos."
    }


@app.get("/social/matrix")
def get_social_environment_matrix():
    """Retorna la matriz de entorno social y mitigación de restricciones del proyecto Capstone."""
    return {
        "poblacion": {
            "total_estimada": 150000,
            "distritos": 12,
            "actores": [
                {"grupo": "Población Vulnerable", "descripcion": "Comunidades campesinas y agricultores en zonas de amortiguamiento."},
                {"grupo": "Personal Operativo", "descripcion": "Bomberos forestales, brigadas de Defensa Civil y Rondas Campesinas."},
                {"grupo": "Autoridades Estratégicas", "descripcion": "Alcaldes, gerentes de GRD y funcionarios de SINAGERD / INDECI."},
                {"grupo": "Científicos y Técnicos", "descripcion": "Investigadores y meteorólogos del SENAMHI."}
            ]
        },
        "muestra_validacion": {
            "n_total": 25,
            "composicion": [
                {"grupo": "Bomberos / Jefes Brigada", "cantidad": 5, "rol": "Validación de mapa de riesgo y coordenadas de alerta"},
                {"grupo": "Rondas Campesinas", "cantidad": 5, "rol": "Recepción y claridad de mensajes WhatsApp/SMS"},
                {"grupo": "Defensa Civil Local", "cantidad": 3, "rol": "Revisión de informes ejecutivos PDF para expedientes"},
                {"grupo": "SENAMHI / Técnicos", "cantidad": 2, "rol": "Validación de variables climáticas ERA5"},
                {"grupo": "Pobladores Rurales", "cantidad": 10, "rol": "Prueba de usabilidad del semáforo Verde/Amarillo/Rojo"}
            ]
        },
        "restricciones_y_mitigaciones": [
            {
                "id": 1,
                "restriccion": "Brecha Digital y Alfabetización Tecnológica",
                "descripcion": "Agricultores mayores de 50 años carecen de smartphones o conectividad mívil rápida.",
                "mitigacion": "El sistema envía alertas SMS/WhatsApp en texto plano con iconografía básica; el Dashboard es exclusivo para bomberos y funcionarios capacitados."
            },
            {
                "id": 2,
                "restriccion": "Desconfianza en Sistemas Automatizados vs. Saber Ancestral",
                "descripcion": "Resistencia a predicciones satelitales por temor a falsas alarmas ('El niño y el lobo').",
                "mitigacion": "Inclusión del porcentaje de confianza del modelo (ej. 85%) y flujo de verificación humana con Rondas Campesinas para alertas amarillas."
            },
            {
                "id": 3,
                "restriccion": "Burocracia y Tiempos de Respuesta Institucionales",
                "descripcion": "Procesos administrativos lentos para autorizar recursos de emergencia.",
                "mitigacion": "Generación automática de Reporte Ejecutivo PDF firmado digitalmente con SHA-256 listo para adjuntar a declaraciones oficiales de emergencia."
            },
            {
                "id": 4,
                "restriccion": "Idiomas y Dialectos Locales",
                "descripcion": "Predominio de dialectos locales (Quechua / Aimara) en zonas rurales.",
                "mitigacion": "Mensajes y mapas con simbología de colores universales (Llama de fuego 🔥, Dirección de viento 💨, Evacuación 🚶)."
            }
        ]
    }


# ─────────────────────────────────────────────
# NASA FIRMS — Focos de calor satelitales reales
# ─────────────────────────────────────────────
import csv
import io
import os
import urllib.request

FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY", "")  # Configura FIRMS_MAP_KEY en .env (ver .env.example)

# Bounding boxes predefinidas (minLon, minLat, maxLon, maxLat)
BBOXES = {
    "peru":       "-81.5,-18.5,-68.5,0",
    "cajamarca":  "-79.4517,-7.7592,-77.7389,-4.5519",
    "norte":      "-80.5,-6.0,-75.0,0",
    "sur":        "-81.5,-18.5,-68.5,-6.0",
    "amazonia":   "-77.0,-14.0,-68.5,-1.0",
}

# Mapa de confianza VIIRS: 'l' = baja, 'n' = nominal, 'h' = alta
CONF_MAP = {"l": 0.40, "n": 0.75, "h": 0.95}


@app.get("/firms/hotspots")
def get_firms_hotspots(
    region: str = Query(default="peru", description="Region preset: peru, cajamarca, norte, sur, amazonia"),
    source: str = Query(default="VIIRS_SNPP_NRT", description="VIIRS_SNPP_NRT | VIIRS_NOAA20_NRT | MODIS_NRT"),
    days: int   = Query(default=1, ge=1, le=7, description="Últimos N días (1-7)"),
):
    """
    Retorna focos de calor satelitales reales de NASA FIRMS en GeoJSON.
    Fuente: VIIRS (375m resolución) o MODIS (1km resolución).
    """
    bbox = BBOXES.get(region, BBOXES["peru"])
    url  = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_MAP_KEY}/{source}/{bbox}/{days}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlertaForestalPeru/2.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error al consultar NASA FIRMS: {exc}")

    reader  = csv.DictReader(io.StringIO(raw))
    features = []

    for row in reader:
        try:
            lat  = float(row["latitude"])
            lon  = float(row["longitude"])
            frp  = float(row.get("frp", 0) or 0)       # Fire Radiative Power (MW)
            conf_raw = row.get("confidence", "n")
            # VIIRS usa 'l'/'n'/'h'; MODIS usa 0-100
            if conf_raw in ("l", "n", "h"):
                confidence = CONF_MAP.get(conf_raw, 0.75)
            else:
                confidence = min(float(conf_raw or 75), 100) / 100.0

            # Clasificar nivel según confianza + FRP
            if confidence >= 0.75 and frp >= 5:
                nivel = "Rojo"
            elif confidence >= 0.50 or frp >= 1:
                nivel = "Amarillo"
            else:
                nivel = "Verde"

            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "satellite":    row.get("satellite", source),
                    "instrument":   row.get("instrument", "VIIRS"),
                    "acq_date":     row.get("acq_date", ""),
                    "acq_time":     row.get("acq_time", ""),
                    "frp":          round(frp, 2),
                    "confidence":   round(confidence, 2),
                    "bright_ti4":   float(row.get("bright_ti4") or row.get("brightness") or 0),
                    "daynight":     row.get("daynight", "D"),
                    "nivel":        nivel,
                    "source":       source,
                }
            })
        except (ValueError, KeyError):
            continue

    return {
        "type":    "FeatureCollection",
        "count":   len(features),
        "region":  region,
        "source":  source,
        "days":    days,
        "features": features,
    }
