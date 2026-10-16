# -*- coding: utf-8 -*-
"""
Utilidades de seguridad de la API de AlertaForestal Perú.

Incluye:
  - get_allowed_origins(): lista blanca de CORS configurable por entorno.
  - require_admin_key(): protege endpoints sensibles (envío de alertas) con una
    API key en la cabecera `X-API-Key`.
  - rate_limit(): limitador en memoria por IP (ventana deslizante) para los
    endpoints públicos de escritura (p. ej. reportes ciudadanos).
  - validate_peru_coords(): rechaza coordenadas fuera del territorio peruano.

Ninguna de estas utilidades requiere dependencias externas.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request

logger = logging.getLogger(__name__)

# Bounding box amplio del Perú (para validar reportes ciudadanos).
PERU_BBOX = {"min_lat": -18.6, "max_lat": 0.2, "min_lon": -81.6, "max_lon": -68.4}

_DEFAULT_ORIGINS = [
    "http://127.0.0.1:5050", "http://localhost:5050",   # portal + API local
    "http://127.0.0.1:8000", "http://localhost:8000",   # API en Docker
    "http://127.0.0.1:8501", "http://localhost:8501",   # dashboard Streamlit
]


def get_allowed_origins() -> list[str]:
    """
    Orígenes permitidos para CORS.

    Se configuran en `ALLOWED_ORIGINS` (lista separada por comas). Por defecto se
    limita a orígenes locales; usar `ALLOWED_ORIGINS=*` para permitir cualquiera
    (no recomendado en producción).
    """
    raw = os.getenv("ALLOWED_ORIGINS", "").strip()
    if not raw:
        return list(_DEFAULT_ORIGINS)
    if raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


_warned_insecure = False


def _warn_insecure_once() -> None:
    global _warned_insecure
    if not _warned_insecure:
        logger.warning(
            "ADMIN_API_KEY no configurada: los endpoints de alerta quedan SIN "
            "protección (modo demo). Defínela en .env para exigir X-API-Key."
        )
        _warned_insecure = True


def require_admin_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """
    Dependencia que exige la cabecera `X-API-Key` cuando `ADMIN_API_KEY` está
    configurada. Si no lo está, permite el acceso (modo demo) y avisa una vez.
    """
    expected = os.getenv("ADMIN_API_KEY", "").strip()
    if not expected:
        _warn_insecure_once()
        return
    if not x_api_key or x_api_key != expected:
        raise HTTPException(
            status_code=401,
            detail="API key inválida o ausente. Envía la cabecera X-API-Key.",
        )


# ── Rate limiting en memoria (ventana deslizante por IP) ──────────────────────
_RATE_LOCK = threading.Lock()
_RATE_HITS: dict[str, deque] = defaultdict(deque)


def rate_limit(max_calls: int, window_seconds: int):
    """
    Devuelve una dependencia que limita a `max_calls` peticiones por IP de cliente
    dentro de una ventana deslizante de `window_seconds` segundos.

    Nota: el estado es en memoria del proceso (suficiente para un despliegue de un
    solo worker). Para varios workers usar Redis/limiter distribuido.
    """

    def _dependency(request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with _RATE_LOCK:
            hits = _RATE_HITS[client]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= max_calls:
                retry = int(window_seconds - (now - hits[0])) + 1
                raise HTTPException(
                    status_code=429,
                    detail=f"Demasiadas solicitudes. Reintenta en {retry} s.",
                    headers={"Retry-After": str(retry)},
                )
            hits.append(now)

    return _dependency


def reset_rate_limiter() -> None:
    """Limpia el estado del rate limiter (útil en tests)."""
    with _RATE_LOCK:
        _RATE_HITS.clear()


def validate_peru_coords(lat: float, lon: float) -> None:
    """Rechaza coordenadas fuera del territorio peruano (HTTP 422)."""
    if not (PERU_BBOX["min_lat"] <= lat <= PERU_BBOX["max_lat"]
            and PERU_BBOX["min_lon"] <= lon <= PERU_BBOX["max_lon"]):
        raise HTTPException(
            status_code=422,
            detail="Coordenadas fuera del territorio peruano.",
        )
