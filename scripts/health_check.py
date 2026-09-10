"""
Script de Health Check automatizado (Entregable Semana 12 del Capstone).
Verifica el estado del servicio FastAPI /health y reinicia el proceso si no responde.

Uso:
    python scripts/health_check.py
"""
import sys
import time
import requests

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

API_HEALTH_URL = "http://localhost:8000/health"
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
