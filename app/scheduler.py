"""
Scheduler de alertas automáticas diarias de riesgo de incendio forestal.

Cada día a las 07:00 (hora de Perú, UTC-5) el sistema:
  1. Consulta las predicciones del modelo LightGBM para toda la región.
  2. Agrupa las grillas por provincia.
  3. Calcula el nivel de riesgo dominante de cada zona.
  4. Envía un mensaje diferenciado al grupo de WhatsApp correspondiente:
       - ROJO    → mensaje de emergencia a todos los grupos + grupo de esa zona.
       - AMARILLO → aviso de precaución al grupo de esa zona.
       - VERDE   → boletín tranquilizador al grupo de esa zona.

Integración con FastAPI (en main.py):
    from app.scheduler import init_scheduler
    init_scheduler(app)

Variables de entorno requeridas (ya en .env):
    GREEN_API_INSTANCE_ID, GREEN_API_TOKEN, WHATSAPP_GROUP_IDS
    
Dependencias adicionales:
    apscheduler>=3.10.0
"""

import logging
import os
from datetime import datetime
from pathlib import Path

import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# Mapeo: nombre de provincia → ChatID de grupo WhatsApp
# El orden debe coincidir con WHATSAPP_GROUP_IDS en .env
# ─────────────────────────────────────────────────────────
ZONAS = [
    {
        "nombre":   "San Marcos",
        "lat_min":  -7.60, "lat_max": -7.20,
        "lon_min": -78.20, "lon_max": -77.90,
        "env_key":  "WA_GROUP_SAN_MARCOS",
    },
    {
        "nombre":   "San Pablo",
        "lat_min":  -7.25, "lat_max": -6.90,
        "lon_min": -79.10, "lon_max": -78.80,
        "env_key":  "WA_GROUP_SAN_PABLO",
    },
    {
        "nombre":   "Bambamarca",
        "lat_min":  -6.80, "lat_max": -6.40,
        "lon_min": -78.70, "lon_max": -78.20,
        "env_key":  "WA_GROUP_BAMBAMARCA",
    },
    {
        "nombre":   "Celendín",
        "lat_min":  -6.95, "lat_max": -6.55,
        "lon_min": -78.30, "lon_max": -77.90,
        "env_key":  "WA_GROUP_CELENDIN",
    },
    {
        "nombre":   "Chota",
        "lat_min":  -6.70, "lat_max": -6.20,
        "lon_min": -79.00, "lon_max": -78.50,
        "env_key":  "WA_GROUP_CHOTA",
    },
    {
        "nombre":   "Cajamarca",
        "lat_min":  -7.30, "lat_max": -6.90,
        "lon_min": -78.70, "lon_max": -78.30,
        "env_key":  "WA_GROUP_CAJAMARCA",
    },
]

API_URL = os.getenv("INTERNAL_API_URL", "http://localhost:8000")


def _get_zone_group_id(zona: dict) -> str | None:
    """Obtiene el ChatID del grupo de una zona desde las variables de entorno."""
    chat_id = os.getenv(zona["env_key"], "").strip()
    return chat_id if chat_id else None


def _fetch_risk_data() -> list[dict]:
    """
    Carga las predicciones de riesgo directamente desde el dataset y el modelo,
    sin hacer una llamada HTTP interna (evita timeout circular).
    """
    try:
        import pandas as pd
        from app.model import RiskModel

        dataset_path = Path(__file__).parent.parent / "data" / "dataset.parquet"
        csv_path = dataset_path.with_suffix(".csv")

        if csv_path.exists():
            df_full = pd.read_csv(csv_path)
        elif dataset_path.exists():
            df_full = pd.read_parquet(dataset_path).drop(columns=["geometry"], errors="ignore")
        else:
            logger.warning("Dataset no encontrado en data/")
            return []

        # Filtrar area de Cajamarca
        df = df_full[
            (df_full["latitude"] >= -7.8) & (df_full["latitude"] <= -6.5) &
            (df_full["longitude"] >= -79.1) & (df_full["longitude"] <= -77.8)
        ].head(2000)

        if df.empty:
            df = df_full.head(2000)

        model = RiskModel()
        feature_cols = [
            "pendiente_pct", "ndvi", "dist_carretera_m", "dist_poblado_m",
            "temp_2m", "humedad_relativa", "viento_velocidad", "viento_direccion"
        ]
        try:
            probas = model.model.predict_proba(df[feature_cols])[:, 1]
        except Exception:
            probas = [0.1] * len(df)

        cell_size = 0.009
        features = []
        for i, (_, row) in enumerate(df.iterrows()):
            proba = float(probas[i])
            nivel = "Rojo" if proba >= 0.70 else "Amarillo" if proba >= 0.35 else "Verde"
            lon, lat = float(row["longitude"]), float(row["latitude"])
            poly_coords = [
                [lon - cell_size/2, lat - cell_size/2],
                [lon + cell_size/2, lat - cell_size/2],
                [lon + cell_size/2, lat + cell_size/2],
                [lon - cell_size/2, lat + cell_size/2],
                [lon - cell_size/2, lat - cell_size/2],
            ]
            features.append({
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [poly_coords]},
                "properties": {
                    "grid_id": str(row.get("grid_id", f"{lon:.4f}_{lat:.4f}")),
                    "probabilidad": round(proba, 4),
                    "nivel": nivel,
                }
            })
        logger.info("Dataset cargado: %d grillas procesadas", len(features))
        return features

    except Exception as exc:
        logger.error("Error al cargar datos de riesgo: %s", exc)
        return []


def _classify_zone(features: list[dict], zona: dict) -> dict:
    """
    Filtra las grillas que caen dentro del bbox de la zona y calcula estadísticas.

    Returns:
        {
          "nombre": str,
          "nivel": "Rojo" | "Amarillo" | "Verde",
          "n_rojas": int,
          "n_amarillas": int,
          "n_total": int,
          "max_proba": float,
          "top_grid": {"grid_id", "lat", "lon", "probabilidad"},
        }
    """
    grillas = [
        f for f in features
        if (
            zona["lat_min"] <= _centroid_lat(f) <= zona["lat_max"]
            and zona["lon_min"] <= _centroid_lon(f) <= zona["lon_max"]
        )
    ]

    if not grillas:
        return {
            "nombre": zona["nombre"],
            "nivel": "Verde",
            "n_rojas": 0,
            "n_amarillas": 0,
            "n_total": 0,
            "max_proba": 0.0,
            "top_grid": None,
        }

    rojas     = [g for g in grillas if g["properties"]["nivel"] == "Rojo"]
    amarillas = [g for g in grillas if g["properties"]["nivel"] == "Amarillo"]

    nivel = "Verde"
    if rojas:
        nivel = "Rojo"
    elif amarillas:
        nivel = "Amarillo"

    # Grilla de mayor riesgo
    top = max(grillas, key=lambda g: g["properties"]["probabilidad"])
    top_lat = _centroid_lat(top)
    top_lon = _centroid_lon(top)

    return {
        "nombre":    zona["nombre"],
        "nivel":     nivel,
        "n_rojas":   len(rojas),
        "n_amarillas": len(amarillas),
        "n_total":   len(grillas),
        "max_proba": round(top["properties"]["probabilidad"], 4),
        "top_grid":  {
            "grid_id":     top["properties"]["grid_id"],
            "lat":         round(top_lat, 5),
            "lon":         round(top_lon, 5),
            "probabilidad": top["properties"]["probabilidad"],
        },
    }


def _centroid_lat(feature: dict) -> float:
    coords = feature["geometry"]["coordinates"][0]
    return sum(c[1] for c in coords) / len(coords)


def _centroid_lon(feature: dict) -> float:
    coords = feature["geometry"]["coordinates"][0]
    return sum(c[0] for c in coords) / len(coords)


def _build_message(zona_info: dict) -> str:
    """Genera el mensaje de WhatsApp según el nivel de riesgo de la zona."""
    now    = datetime.now().strftime("%d/%m/%Y %H:%M")
    nombre = zona_info["nombre"]
    nivel  = zona_info["nivel"]
    n_r    = zona_info["n_rojas"]
    n_a    = zona_info["n_amarillas"]
    n_tot  = zona_info["n_total"]
    proba  = zona_info["max_proba"]
    top    = zona_info["top_grid"]

    mapa_url = ""
    if top:
        mapa_url = f"https://www.google.com/maps?q={top['lat']},{top['lon']}"

    if nivel == "Rojo":
        return (
            f"🚨 *ALERTA ROJA — PELIGRO DE INCENDIO FORESTAL*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 Zona: *{nombre}*\n"
            f"📅 Fecha/hora: {now}\n"
            f"🔴 Grillas en peligro alto: *{n_r}*\n"
            f"🟡 Grillas en precaución:   *{n_a}*\n"
            f"🤖 Probabilidad máxima: *{proba:.0%}*\n"
            f"🗺️ Punto crítico: {mapa_url}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *Acciones inmediatas:*\n"
            f"  • Alerta a Defensa Civil y Bomberos (📞 116)\n"
            f"  • No encender fuego en ningún punto\n"
            f"  • Comunica a vecinos y rondas campesinas\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"_Sistema Nacional de Alerta Temprana — AlertaForestal Perú_"
        )
    elif nivel == "Amarillo":
        return (
            f"⚠️ *AVISO DE PRECAUCIÓN — Riesgo Moderado*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 Zona: *{nombre}*\n"
            f"📅 Fecha/hora: {now}\n"
            f"🟡 Grillas en precaución: *{n_a}* de {n_tot}\n"
            f"🤖 Probabilidad máxima: *{proba:.0%}*\n"
            f"🗺️ Zona de mayor riesgo: {mapa_url}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 *Recomendaciones:*\n"
            f"  • Evita quemas agrícolas hoy\n"
            f"  • Mantente atento al clima de la tarde\n"
            f"  • Si detectas humo, repórtalo en el portal\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"_Sistema Nacional de Alerta Temprana — AlertaForestal Perú_"
        )
    else:
        return (
            f"✅ *BOLETÍN DIARIO — Riesgo Bajo*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 Zona: *{nombre}*\n"
            f"📅 Fecha/hora: {now}\n"
            f"🟢 Condiciones actuales: *Favorables*\n"
            f"📊 Grillas analizadas: {n_tot}\n"
            f"🤖 Probabilidad máxima: *{proba:.0%}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Hoy no se detecta riesgo significativo en tu zona. "
            f"Continúa aplicando buenas prácticas forestales.\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"_Sistema Nacional de Alerta Temprana — AlertaForestal Perú_"
        )


async def run_daily_alerts() -> None:
    """
    Tarea principal del scheduler:
    - Descarga las predicciones de riesgo de hoy.
    - Para cada zona, calcula el nivel de riesgo y envía el mensaje al grupo correspondiente.
    """
    logger.info("🕐 Iniciando envío de alertas automáticas diarias...")

    try:
        instance_id, token, _ = _get_config()
    except RuntimeError as exc:
        logger.error("⛔ Scheduler: credenciales no configuradas — %s", exc)
        return

    features = _fetch_risk_data()
    if not features:
        logger.warning("⚠️  Scheduler: no hay datos de riesgo disponibles hoy.")
        return

    logger.info("📊 %d grillas cargadas. Analizando por zona...", len(features))

    for zona in ZONAS:
        chat_id = _get_zone_group_id(zona)
        if not chat_id:
            logger.warning(
                "⚠️  Sin ChatID para zona %s (env_key: %s). Saltando.",
                zona["nombre"], zona["env_key"]
            )
            continue

        zona_info = _classify_zone(features, zona)
        mensaje   = _build_message(zona_info)

        try:
            result = _send_message(instance_id, token, chat_id, mensaje)
            logger.info(
                "✅ Alerta %s → %s (%s) | respuesta: %s",
                zona_info["nivel"], zona["nombre"], chat_id, result
            )
        except Exception as exc:
            logger.error(
                "❌ Error al enviar alerta a %s (%s): %s",
                zona["nombre"], chat_id, exc
            )

    logger.info("🏁 Envío de alertas diarias completado.")


def init_scheduler(app) -> AsyncIOScheduler:
    """
    Inicializa y arranca el scheduler dentro de la aplicación FastAPI.

    Uso en main.py:
        from app.scheduler import init_scheduler
        init_scheduler(app)

    Horario: todos los días a las 07:00 hora de Perú (America/Lima = UTC-5).
    """
    scheduler = AsyncIOScheduler(timezone="America/Lima")

    scheduler.add_job(
        run_daily_alerts,
        trigger=CronTrigger(hour=7, minute=0, timezone="America/Lima"),
        id="daily_wildfire_alerts",
        name="Alertas diarias de incendio por WhatsApp",
        replace_existing=True,
    )

    @app.on_event("startup")
    async def start_scheduler():
        scheduler.start()
        logger.info(
            "⏰ Scheduler iniciado — alertas diarias programadas para las 07:00 (Lima)"
        )

    @app.on_event("shutdown")
    async def stop_scheduler():
        scheduler.shutdown(wait=False)
        logger.info("🛑 Scheduler detenido.")

    return scheduler
