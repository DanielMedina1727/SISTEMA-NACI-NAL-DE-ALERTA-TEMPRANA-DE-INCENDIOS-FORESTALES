# -*- coding: utf-8 -*-
"""
Actualización meteorológica EN VIVO para Cajamarca usando Open-Meteo Forecast API
(100 % gratuita, sin API key, ~1.5 s para toda la región).

Permite que las predicciones del mapa de riesgo IA (`GET /risk/today`) y las
alertas diarias de las 07:00 AM reflejen las condiciones climáticas REALES de hoy
(temperatura, humedad relativa, viento, días sin lluvia, lluvia acumulada 7/15 d,
VPD e índice de sequedad) en lugar de quedar fijas al snapshot estático.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests
from scipy.spatial import cKDTree

from app.model import compute_physical_features

logger = logging.getLogger(__name__)

CAJAMARCA_BBOX = (-7.7592, -79.4517, -4.5519, -77.7389)  # min_lat, min_lon, max_lat, max_lon
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
_UA = {"User-Agent": "AlertaForestalPeru/2.5"}


def _grid_points(bbox: tuple[float, float, float, float] = CAJAMARCA_BBOX, step: float = 0.45) -> list[tuple[float, float]]:
    min_lat, min_lon, max_lat, max_lon = bbox
    lats = np.arange(min_lat, max_lat + 1e-6, step)
    lons = np.arange(min_lon, max_lon + 1e-6, step)
    return [(float(lon), float(lat)) for lat in lats for lon in lons]


def fetch_today_meteo(bbox: tuple[float, float, float, float] = CAJAMARCA_BBOX, step: float = 0.45) -> pd.DataFrame:
    """
    Descarga los últimos 15 días + hoy de Open-Meteo para una rejilla sobre Cajamarca
    en una sola petición HTTP (~32-40 puntos, ~1.5 s).
    """
    puntos = _grid_points(bbox, step=step)
    lats = ",".join(f"{p[1]:.4f}" for p in puntos)
    lons = ",".join(f"{p[0]:.4f}" for p in puntos)

    resp = requests.get(
        OPEN_METEO_URL,
        params={
            "latitude": lats,
            "longitude": lons,
            "past_days": 15,
            "forecast_days": 1,
            "daily": ",".join([
                "temperature_2m_mean",
                "relative_humidity_2m_mean",
                "wind_speed_10m_mean",
                "wind_direction_10m_dominant",
                "precipitation_sum",
            ]),
            "timezone": "America/Lima",
        },
        headers=_UA,
        timeout=25,
    )
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        data = [data]

    filas = []
    for punto, item in zip(puntos, data):
        daily = item.get("daily") or {}
        t = daily.get("temperature_2m_mean") or []
        h = daily.get("relative_humidity_2m_mean") or []
        wv = daily.get("wind_speed_10m_mean") or []
        wd = daily.get("wind_direction_10m_dominant") or []
        pr = daily.get("precipitation_sum") or []
        if not t:
            continue

        t_arr = np.array([np.nan if v is None else float(v) for v in t], dtype=float)
        h_arr = np.array([np.nan if v is None else float(v) for v in h], dtype=float)
        wv_arr = np.array([np.nan if v is None else float(v) for v in wv], dtype=float)
        wd_arr = np.array([np.nan if v is None else float(v) for v in wd], dtype=float)
        pr_arr = np.array([0.0 if v is None else float(v) for v in pr], dtype=float)

        # Días consecutivos sin lluvia (<1 mm) hasta hoy
        dias = 0
        for p_val in pr_arr[::-1]:
            if p_val < 1.0:
                dias += 1
            else:
                break

        def _mean_last(arr: np.ndarray, n: int, fallback: float) -> float:
            sub = arr[-n:]
            val = float(np.nanmean(sub)) if len(sub) and not np.all(np.isnan(sub)) else fallback
            return fallback if np.isnan(val) else val

        ang = np.deg2rad(wd_arr[-3:])
        s_m = float(np.nanmean(np.sin(ang))) if len(ang) else 0.7071
        c_m = float(np.nanmean(np.cos(ang))) if len(ang) else 0.7071
        dir_vec = float(np.rad2deg(np.arctan2(s_m, c_m)) % 360.0)

        t_prev = float(t_arr[-2]) if len(t_arr) >= 2 and not np.isnan(t_arr[-2]) else _mean_last(t_arr, 3, 20.0)
        h_prev = float(h_arr[-2]) if len(h_arr) >= 2 and not np.isnan(h_arr[-2]) else _mean_last(h_arr, 3, 55.0)

        filas.append({
            "longitude": punto[0],
            "latitude": punto[1],
            "temp_2m": round(_mean_last(t_arr, 3, 20.0), 2),
            "humedad_relativa": round(_mean_last(h_arr, 3, 55.0), 2),
            "viento_velocidad": round(_mean_last(wv_arr, 3, 12.0), 2),
            "viento_direccion": round(dir_vec, 1),
            "dias_sin_lluvia": int(dias),
            "lluvia_acum_7d": round(float(np.nansum(pr_arr[-7:])), 2),
            "lluvia_acum_15d": round(float(np.nansum(pr_arr[-15:])), 2),
            "temp_lag1": round(t_prev, 2),
            "humedad_lag1": round(h_prev, 2),
        })

    return pd.DataFrame(filas)


def apply_live_weather(df: pd.DataFrame, meteo_df: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """
    Aplica la meteorología real de HOY sobre un DataFrame de grillas de Cajamarca
    usando interpolación IDW (k=4) + vecindario KNN geográfico + 3 variables físicas.
    Devuelve (df_actualizado, info_dict).
    """
    if meteo_df is None:
        meteo_df = fetch_today_meteo()

    if meteo_df.empty:
        raise RuntimeError("Open-Meteo devolvió 0 puntos meteorológicos.")

    out = df.copy()
    grid_coords = np.column_stack([out["longitude"].to_numpy(float), out["latitude"].to_numpy(float)])
    m_coords = np.column_stack([meteo_df["longitude"].to_numpy(float), meteo_df["latitude"].to_numpy(float)])

    k = min(4, len(m_coords))
    dists, idxs = cKDTree(m_coords).query(grid_coords, k=k)
    if k == 1:
        dists, idxs = dists[:, None], idxs[:, None]
    w = 1.0 / np.maximum(dists, 1e-4)
    w /= w.sum(axis=1, keepdims=True)

    for col in (
        "temp_2m", "humedad_relativa", "viento_velocidad",
        "dias_sin_lluvia", "lluvia_acum_7d", "lluvia_acum_15d",
        "temp_lag1", "humedad_lag1",
    ):
        vals = meteo_df[col].to_numpy(float)[idxs]
        out[col] = np.round(np.sum(vals * w, axis=1), 2)

    # Dirección del viento por promedio vectorial circular (sin/cos)
    ang = np.deg2rad(meteo_df["viento_direccion"].to_numpy(float)[idxs])
    s_mean = np.sum(np.sin(ang) * w, axis=1)
    c_mean = np.sum(np.cos(ang) * w, axis=1)
    norm = np.maximum(np.hypot(s_mean, c_mean), 1e-6)
    out["viento_dir_sin"] = np.round(s_mean / norm, 4)
    out["viento_dir_cos"] = np.round(c_mean / norm, 4)
    out["viento_direccion"] = np.round(np.rad2deg(np.arctan2(s_mean, c_mean)) % 360.0, 1)

    # Vecindario geográfico KNN (k=8, excluyendo la propia celda)
    lats = out["latitude"].to_numpy(float)
    lons = out["longitude"].to_numpy(float)
    lat0 = np.deg2rad(float(lats.mean()))
    geo_km = np.column_stack([lons * 111.32 * np.cos(lat0), lats * 110.57])
    kk = max(1, min(9, len(out)))
    _, knn_idx = cKDTree(geo_km).query(geo_km, k=kk)
    if knn_idx.ndim == 1:
        knn_idx = knn_idx[:, None]
    neigh = knn_idx[:, 1:] if knn_idx.shape[1] > 1 else knn_idx

    out["temp_vecindad_media"] = np.round(out["temp_2m"].to_numpy(float)[neigh].mean(axis=1), 1)
    out["humedad_vecindad_media"] = np.round(out["humedad_relativa"].to_numpy(float)[neigh].mean(axis=1), 1)

    # Recalcular variables físicas compuestas (VPD, viento×pendiente, índice de sequedad)
    vpd, vp, seq = compute_physical_features(
        out["temp_2m"].to_numpy(float),
        out["humedad_relativa"].to_numpy(float),
        out["viento_velocidad"].to_numpy(float),
        out["pendiente_pct"].to_numpy(float),
        out["dias_sin_lluvia"].to_numpy(float),
    )
    out["vpd_kpa"] = vpd
    out["viento_pendiente"] = vp
    out["indice_sequedad"] = seq

    now_iso = datetime.now(timezone.utc).isoformat()
    info = {
        "source": "open-meteo-live",
        "updated_at": now_iso,
        "points": int(len(meteo_df)),
        "temp_mean": round(float(out["temp_2m"].mean()), 2),
        "humidity_mean": round(float(out["humedad_relativa"].mean()), 1),
        "rain_7d_mean": round(float(out["lluvia_acum_7d"].mean()), 2),
    }
    logger.info(
        "🌤️ Clima en vivo aplicado (%d pts Open-Meteo): T=%.1f°C, HR=%.0f%%, lluvia7d=%.1fmm",
        info["points"], info["temp_mean"], info["humidity_mean"], info["rain_7d_mean"],
    )
    return out, info
