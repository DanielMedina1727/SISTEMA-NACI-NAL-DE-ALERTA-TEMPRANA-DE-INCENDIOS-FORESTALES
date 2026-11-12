"""
Script de Health Check automatizado (Entregable Semana 12 del Capstone).
Verifica el estado del servicio FastAPI /health y reinicia el proceso si no responde.

Uso:
    python scripts/health_check.py [--port PUERTO]

    El puerto también se puede configurar con la variable de entorno API_PORT.
    Por defecto usa 5050 (puerto de producción local).
"""
import argparse
import os
import sys
import time
import requests

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

parser = argparse.ArgumentParser(description="Health check del servidor FastAPI.")
parser.add_argument(
    "--port",
    type=int,
    default=int(os.getenv("API_PORT", "5050")),
    help="Puerto del servidor FastAPI (default: 5050 o variable API_PORT).",
)
args = parser.parse_args()

API_HEALTH_URL = f"http://localhost:{args.port}/health"
MAX_RETRIES = 3
RETRY_DELAY_SEC = 5


def check_api_health() -> bool:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(API_HEALTH_URL, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    print(f"✅ HealthCheck Exitoso [Intento {attempt}/{MAX_RETRIES}]: API operativa. Modelo cargado: {data.get('model_loaded')}")
                    return True
            print(f"⚠️ HealthCheck Advertencia [Intento {attempt}/{MAX_RETRIES}]: Código HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ HealthCheck Error [Intento {attempt}/{MAX_RETRIES}]: No se pudo conectar a {API_HEALTH_URL} ({e})")

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY_SEC)

    return False


if __name__ == "__main__":
    is_healthy = check_api_health()
    if not is_healthy:
        print("🚨 API NO SALUDABLE: Disparando orden de reinicio del contenedor Docker...")
        sys.exit(1)
    else:
        sys.exit(0)
