"""
Envía una alerta a Telegram cuando una grilla pasa a nivel Rojo.

Configura TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en tu .env
(crea el bot hablando con @BotFather en Telegram).
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_red_alert(grid_id: str, lat: float, lon: float, confianza: float):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Configura TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en .env")

    mapa_url = f"https://www.google.com/maps?q={lat},{lon}"
    mensaje = (
        f"🔴 ALERTA ROJA - Riesgo de incendio\n"
        f"Grilla: {grid_id}\n"
        f"Coordenadas: {lat:.4f}, {lon:.4f}\n"
        f"Confianza del modelo: {confianza:.0%}\n"
        f"Mapa: {mapa_url}"
    )

    response = requests.post(
        TELEGRAM_API.format(token=token),
        data={"chat_id": chat_id, "text": mensaje},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    # Prueba manual
    send_red_alert(grid_id="-78.5000_-7.1600", lat=-7.16, lon=-78.5, confianza=0.85)
