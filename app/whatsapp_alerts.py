"""
Envía alertas de incendio forestal a grupos de WhatsApp usando Green API.

Green API es un servicio freemium que permite enviar mensajes a grupos reales de WhatsApp
vinculando tu número mediante código QR (sin necesidad de WhatsApp Business ni META).

Configuración rápida (5 minutos):
  1. Regístrate en https://green-api.com/ (plan Developer gratuito)
  2. Crea una instancia → copia idInstance y apiTokenInstance al .env
  3. En el panel, haz clic en "Escanear QR" y escanea con tu WhatsApp
  4. En el panel → métodos API → getChats → ejecutar → copia los IDs de grupo
     (tienen el formato 120363XXXXXXXXXXXXXXXX@g.us)
  5. Pega los IDs en WHATSAPP_GROUP_IDS separados por coma en el .env

Variables de entorno requeridas en .env:
  GREEN_API_INSTANCE_ID  → ID de tu instancia en Green API
  GREEN_API_TOKEN        → Token de tu instancia en Green API
  WHATSAPP_GROUP_IDS     → ChatIDs separados por coma (grupos y/o números)
                           Grupo:   120363XXXXXXXXXXXXXXXX@g.us
                           Persona: 51987654321@c.us
"""

import logging
import os
import time
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Base URL de Green API
_GREEN_API_BASE = "https://api.green-api.com/waInstance{instance_id}/{method}/{token}"


def _get_config() -> tuple[str, str, list[str]]:
    """Obtiene y valida las variables de entorno de Green API."""
    instance_id = os.getenv("GREEN_API_INSTANCE_ID", "").strip()
    token = os.getenv("GREEN_API_TOKEN", "").strip()
    group_ids_raw = os.getenv("WHATSAPP_GROUP_IDS", "").strip()

    if not instance_id or instance_id == "tu_id_de_instancia":
        raise RuntimeError(
            "Falta GREEN_API_INSTANCE_ID en .env — "
            "regístrate en https://green-api.com/ y copia tu idInstance."
        )
    if not token or token == "tu_token_de_instancia":
        raise RuntimeError(
            "Falta GREEN_API_TOKEN en .env — "
            "copia el apiTokenInstance desde el panel de Green API."
        )
    if not group_ids_raw or "XXXX" in group_ids_raw:
        raise RuntimeError(
            "Falta WHATSAPP_GROUP_IDS en .env — "
            "usa el método getChats en el panel de Green API para obtener los IDs de tus grupos."
        )

    group_ids = [gid.strip() for gid in group_ids_raw.split(",") if gid.strip()]
    return instance_id, token, group_ids


def _send_message(instance_id: str, token: str, chat_id: str, message: str,
                  max_retries: int = 3) -> dict:
    """
    Envía un mensaje de texto a un chatId específico usando Green API.

    Reintenta con backoff exponencial (1s, 2s, 4s) ante errores transitorios
    (429 Too Many Requests o 5xx), habituales en los planes gratuitos.
    """
    url = _GREEN_API_BASE.format(
        instance_id=instance_id,
        method="sendMessage",
        token=token,
    )
    payload = {
        "chatId": chat_id,
        "message": message,
    }

    last_exc: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                raise requests.HTTPError(f"HTTP {response.status_code}", response=response)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    raise last_exc if last_exc else RuntimeError("Fallo desconocido al enviar mensaje")


def send_red_alert(
    grid_id: str,
    lat: float,
    lon: float,
    confianza: float,
    nivel: str = "ROJO 🔴",
    extra_info: Optional[str] = None,
) -> list[dict]:
    """
    Envía una alerta de incendio forestal a todos los grupos configurados en .env.

    Args:
        grid_id:    Identificador de la grilla detectada.
        lat:        Latitud del punto de alerta.
        lon:        Longitud del punto de alerta.
        confianza:  Confianza del modelo (0.0 – 1.0).
        nivel:      Nivel de alerta (por defecto "ROJO 🔴").
        extra_info: Información adicional opcional para incluir en el mensaje.

    Returns:
        Lista de respuestas JSON de Green API (una por grupo/número).
    """
    instance_id, token, group_ids = _get_config()

    mapa_url = f"https://www.google.com/maps?q={lat},{lon}"
    mensaje = (
        f"🔥 *ALERTA TEMPRANA DE INCENDIO FORESTAL*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ Nivel: *{nivel}*\n"
        f"📍 Grilla: {grid_id}\n"
        f"🌐 Coordenadas: {lat:.4f}, {lon:.4f}\n"
        f"🤖 Confianza del modelo: *{confianza:.0%}*\n"
        f"🗺️ Ver en mapa: {mapa_url}"
    )

    if extra_info:
        mensaje += f"\n\nℹ️ {extra_info}"

    mensaje += (
        "\n━━━━━━━━━━━━━━━━━━━━\n"
        "_Sistema Nacional de Alerta Temprana de Incendios Forestales_"
    )

    results = []
    for chat_id in group_ids:
        try:
            result = _send_message(instance_id, token, chat_id, mensaje)
            logger.info("✅ Alerta enviada a %s → %s", chat_id, result)
            results.append({"chat_id": chat_id, "status": "ok", "response": result})
        except requests.HTTPError as e:
            logger.error("❌ Error HTTP al enviar a %s: %s", chat_id, e)
            results.append({"chat_id": chat_id, "status": "error", "error": str(e)})
        except Exception as e:
            logger.error("❌ Error inesperado al enviar a %s: %s", chat_id, e)
            results.append({"chat_id": chat_id, "status": "error", "error": str(e)})

    return results


def send_alert_by_level(
    grid_id: str,
    lat: float,
    lon: float,
    confianza: float,
    nivel_numerico: int,
) -> list[dict]:
    """
    Envía alerta seleccionando el emoji/etiqueta según el nivel de riesgo (1-3).

    Args:
        nivel_numerico: 1 = AMARILLO, 2 = AMARILLO (vigilancia reforzada), 3 = ROJO
                        (se unifica "Naranja" en "Amarillo" para no confundir al ciudadano)
    """
    niveles = {
        1: "AMARILLO 🟡",
        2: "AMARILLO 🟡",
        3: "ROJO 🔴",
    }
    nivel = niveles.get(nivel_numerico, "ROJO 🔴")
    return send_red_alert(grid_id=grid_id, lat=lat, lon=lon, confianza=confianza, nivel=nivel)


def get_linked_groups() -> list[dict]:
    """
    Consulta Green API para listar todos los chats (grupos e individuales) disponibles.
    Útil para descubrir el chatId de tus grupos y configurar WHATSAPP_GROUP_IDS.

    Returns:
        Lista de chats con id, name y type.
    """
    instance_id, token, _ = _get_config()
    url = _GREEN_API_BASE.format(
        instance_id=instance_id,
        method="getChats",
        token=token,
    )
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    chats = response.json()

    # Filtrar solo grupos
    grupos = [
        {"id": c.get("id"), "name": c.get("name"), "type": c.get("type")}
        for c in chats
        if c.get("id", "").endswith("@g.us")
    ]
    return grupos


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("\n📋 Listando grupos vinculados a tu instancia de Green API...\n")
    try:
        grupos = get_linked_groups()
        if grupos:
            print(f"Encontrados {len(grupos)} grupo(s):\n")
            for g in grupos:
                print(f"  Nombre : {g['name']}")
                print(f"  ChatID : {g['id']}  ← copia esto en WHATSAPP_GROUP_IDS")
                print()
        else:
            print("No se encontraron grupos. Asegúrate de que el número esté en algún grupo.")
    except RuntimeError as e:
        print(f"⚠️  {e}")
        print("\nConfigura primero GREEN_API_INSTANCE_ID, GREEN_API_TOKEN y WHATSAPP_GROUP_IDS en tu .env")
    except Exception as e:
        print(f"❌ Error al consultar Green API: {e}")

    print("\n📤 Enviando alerta de prueba...\n")
    try:
        resultados = send_red_alert(
            grid_id="-78.5000_-7.1600",
            lat=-7.16,
            lon=-78.5,
            confianza=0.85,
        )
        print(json.dumps(resultados, indent=2, ensure_ascii=False))
    except RuntimeError as e:
        print(f"⚠️  {e}")
