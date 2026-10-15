# -*- coding: utf-8 -*-
"""
Adquisición de características REALES para el dataset de riesgo de incendios.
Todas las fuentes son abiertas y SIN necesidad de credenciales:

  - Meteorología (ERA5)          -> Open-Meteo Archive API   (https://open-meteo.com)
  - Elevación / Pendiente / Aspecto -> Copernicus DEM GLO-30 (AWS Open Data)
  - NDVI                          -> Sentinel-2 L2A           (AWS Open Data, STAC Element84)
  - Distancias a vías y poblados  -> OpenStreetMap             (Overpass API)

Los resultados se cachean en data/cache/ para no volver a descargarlos.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).parent.parent
CACHE = ROOT / "data" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "AlertaForestalPeru/2.0 (capstone; contacto: dev@alertaforestal.pe)"}
TIMEOUT = 90

# ─────────────────────────────────────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────────────────────────────────────

def _log(msg: str):
    print(f"  [real_features] {msg}")


def _rl_get(url, params=None, sleep=1.0, **kw):
    """GET con reintentos y respeto de rate-limit."""
    last = None
    for intento in range(4):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=TIMEOUT, **kw)
            if r.status_code == 429:
                time.sleep(5 * (intento + 1))
                continue
            r.raise_for_status()
            return r
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(sleep * (intento + 1))
    raise RuntimeError(f"Fallo al consultar {url}: {last}")


# ─────────────────────────────────────────────────────────────────────────────
# 1) METEOROLOGÍA REAL — ERA5 vía Open-Meteo Archive
# ─────────────────────────────────────────────────────────────────────────────

def _meteo_grid_points(bbox, step=0.25):
    min_lat, min_lon, max_lat, max_lon = bbox
    lats = np.arange(min_lat, max_lat + 1e-9, step)
    lons = np.arange(min_lon, max_lon + 1e-9, step)
    return [(float(lon), float(lat)) for lat in lats for lon in lons]


def fetch_meteo(bbox, ref_date, ventana_dias=20, step=0.25):
    """
    Descarga ERA5 real (Open-Meteo) para una rejilla de puntos y agrega las
    variables meteorológicas que necesita el modelo. Devuelve un DataFrame con
    columnas: longitude, latitude, temp_2m, humedad_relativa, viento_velocidad,
    viento_direccion, dias_sin_lluvia, lluvia_acum_7d, lluvia_acum_15d,
    temp_lag1, humedad_lag1.
    """
    cache_f = CACHE / f"meteo_{ref_date}_{ventana_dias}d.npz"
    puntos = _meteo_grid_points(bbox, step)
    if cache_f.exists():
        z = np.load(cache_f, allow_pickle=True)
        _log(f"meteo: caché -> {cache_f.name}")
        return pd.DataFrame(z["df"].tolist())

    ref = pd.Timestamp(ref_date)
    inicio = (ref - pd.Timedelta(days=ventana_dias)).date().isoformat()
    fin = ref.date().isoformat()

    filas = []
    chunk = 50
    for i in range(0, len(puntos), chunk):
        sub = puntos[i:i + chunk]
        lats = ",".join(f"{p[1]:.4f}" for p in sub)
        lons = ",".join(f"{p[0]:.4f}" for p in sub)
        r = requests.post(
            "https://archive-api.open-meteo.com/v1/archive",
            data={
                "latitude": lats, "longitude": lons,
                "start_date": inicio, "end_date": fin,
                "daily": ",".join([
                    "temperature_2m_mean", "relative_humidity_2m_mean",
                    "wind_speed_10m_mean", "wind_direction_10m_dominant",
                    "precipitation_sum",
                ]),
                "timezone": "America/Lima",
            },
            headers=UA, timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            data = [data]
        for punto, d in zip(sub, data):
            daily = d.get("daily", {})
            t = daily.get("temperature_2m_mean") or []
            h = daily.get("relative_humidity_2m_mean") or []
            wv = daily.get("wind_speed_10m_mean") or []
            wd = daily.get("wind_direction_10m_dominant") or []
            pr = daily.get("precipitation_sum") or []
            if not t:
                continue
            t = np.array([np.nan if v is None else v for v in t], float)
            h = np.array([np.nan if v is None else v for v in h], float)
            wv = np.array([np.nan if v is None else v for v in wv], float)
            wd = np.array([np.nan if v is None else v for v in wd], float)
            pr = np.array([0.0 if v is None else v for v in pr], float)

            # Días consecutivos sin lluvia (<1 mm) terminando en ref_date
            dias = 0
            for precip in pr[::-1]:
                if precip < 1.0:
                    dias += 1
                else:
                    break

            def _media(arr, n):
                v = arr[-n:]
                return float(np.nanmean(v)) if len(v) else np.nan

            ang = np.deg2rad(wd[-3:])
            dir_vec = np.rad2deg(np.arctan2(np.nanmean(np.sin(ang)), np.nanmean(np.cos(ang)))) % 360

            filas.append({
                "longitude": punto[0], "latitude": punto[1],
                "temp_2m": round(_media(t, 3), 2),
                "humedad_relativa": round(_media(h, 3), 2),
                "viento_velocidad": round(_media(wv, 3), 2),
                "viento_direccion": round(float(dir_vec), 1),
                "dias_sin_lluvia": int(dias),
                "lluvia_acum_7d": round(float(np.nansum(pr[-7:])), 2),
                "lluvia_acum_15d": round(float(np.nansum(pr[-15:])), 2),
                "temp_lag1": round(float(t[-2]) if len(t) >= 2 else np.nan, 2),
                "humedad_lag1": round(float(h[-2]) if len(h) >= 2 else np.nan, 2),
            })
        time.sleep(0.3)

    df = pd.DataFrame(filas)
    if not df.empty:
        np.savez_compressed(cache_f, df=df.to_dict("records"))
    _log(f"meteo: {len(df)} puntos ERA5 reales descargados ({inicio}..{fin})")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 2) ELEVACIÓN / PENDIENTE / ASPECTO REALES — Copernicus DEM GLO-30
# ─────────────────────────────────────────────────────────────────────────────

_DEM_URL = ("https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/"
            "Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM/"
            "Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM.tif")


def _dem_tile_name(sw_lat, sw_lon):
    ns = "N" if sw_lat >= 0 else "S"
    ew = "E" if sw_lon >= 0 else "W"
    return _DEM_URL.format(ns=ns, lat=abs(sw_lat), ew=ew, lon=abs(sw_lon))


def _dem_tiles(bbox):
    min_lat, min_lon, max_lat, max_lon = bbox
    tiles = []
    for lat in range(math.floor(min_lat), math.floor(max_lat) + 1):
        for lon in range(math.floor(min_lon), math.floor(max_lon) + 1):
            tiles.append((lat, lon))
    return tiles


def _read_dem_tile(sw_lat, sw_lon, decim=4):
    """Lee una tesela DEM (reducida) y calcula pendiente (%) y aspecto (grados)."""
    import rasterio

    cache_f = CACHE / f"dem_{sw_lat}_{sw_lon}_{decim}.npz"
    if cache_f.exists():
        z = np.load(cache_f)
        return z["elev"], z["slope"], z["aspect"]

    url = _dem_tile_name(sw_lat, sw_lon)
    n = 3600 // decim
    with rasterio.open(url) as ds:
        elev = ds.read(1, out_shape=(n, n)).astype("float32")
    elev[elev <= -1000] = np.nan
    # Resolución efectiva en metros (~30 m * decim)
    res_m = 30.0 * decim
    gy, gx = np.gradient(elev, res_m, res_m)
    slope = np.sqrt(gx ** 2 + gy ** 2) * 100.0          # pendiente en %
    aspect = (np.rad2deg(np.arctan2(-gx, gy)) + 360.0) % 360.0  # 0=N, 90=E
    np.savez_compressed(cache_f, elev=elev, slope=slope, aspect=aspect)
    _log(f"DEM tesela {sw_lat},{sw_lon} descargada ({n}x{n})")
    return elev, slope, aspect


def build_dem_layer(bbox, decim=4):
    """Carga (y cachea) todas las teselas DEM del bbox. Devuelve dict {(sw_lat,sw_lon): arrays}."""
    layer = {}
    for sw_lat, sw_lon in _dem_tiles(bbox):
        try:
            layer[(sw_lat, sw_lon)] = _read_dem_tile(sw_lat, sw_lon, decim)
        except Exception as exc:  # noqa: BLE001
            _log(f"⚠️ DEM tesela {sw_lat},{sw_lon} no disponible: {exc}")
    return layer


def sample_dem(layer, lons, lats, decim=4):
    """Muestrea elevación, pendiente y aspecto para arreglos de lon/lat."""
    n = 3600 // decim
    res = 1.0 / n
    elev = np.full(len(lons), np.nan, "float32")
    slope = np.full(len(lons), np.nan, "float32")
    aspect = np.full(len(lons), np.nan, "float32")
    triples = zip(range(len(lons)), lons, lats)
    for i, lon, lat in triples:
        key = (math.floor(lat), math.floor(lon))
        arrs = layer.get(key)
        if arrs is None:
            continue
        e, s, a = arrs
        row = int((key[0] + 1 - lat) / res)
        col = int((lon - key[1]) / res)
        if 0 <= row < e.shape[0] and 0 <= col < e.shape[1]:
            elev[i], slope[i], aspect[i] = e[row, col], s[row, col], a[row, col]
    return elev, slope, aspect


# ─────────────────────────────────────────────────────────────────────────────
# 3) NDVI REAL — Sentinel-2 L2A (AWS Open Data, STAC Element84)
# ─────────────────────────────────────────────────────────────────────────────

_STAC = "https://earth-search.aws.element84.com/v1/search"


def fetch_ndvi_mosaic(bbox, start, end, res=0.005, max_scenes=10, cloud_lt=40):
    """
    Construye un mosaico NDVI real (mediana) a partir de escenas Sentinel-2 L2A.
    Devuelve (ndvi_array, transform) en EPSG:4326, o (None, None) si no hay datos.
    """
    cache_f = CACHE / "ndvi_mosaic.npz"
    if cache_f.exists():
        z = np.load(cache_f)
        _log("NDVI: caché de mosaico")
        return z["ndvi"], z["transform"]

    import rasterio
    from rasterio.transform import from_origin
    from rasterio.warp import reproject, Resampling
    from pyproj import Transformer

    r = requests.post(_STAC, json={
        "collections": ["sentinel-2-l2a"],
        "bbox": [bbox[1], bbox[0], bbox[3], bbox[2]],  # STAC: [west, south, east, north]
        "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
        "limit": 40,
        "query": {"eo:cloud_cover": {"lt": cloud_lt}},
    }, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    feats = r.json().get("features", [])
    # Ordenar por menor nubosidad
    feats.sort(key=lambda f: f["properties"].get("eo:cloud_cover", 100))
    feats = feats[:max_scenes]
    _log(f"NDVI: {len(feats)} escenas Sentinel-2 encontradas")
    if not feats:
        return None, None

    min_lat, min_lon, max_lat, max_lon = bbox
    width = int((max_lon - min_lon) / res) + 1
    height = int((max_lat - min_lat) / res) + 1
    dst_transform = from_origin(min_lon, max_lat, res, res)

    escenas_ok = 0
    stack = np.full((len(feats), height, width), np.nan, "float32")
    for k, feat in enumerate(feats):
        try:
            red_href = feat["assets"]["red"]["href"]
            nir_href = feat["assets"]["nir"]["href"]
            with rasterio.open(red_href) as dred, rasterio.open(nir_href) as dnir:
                src_crs = dred.crs
                src_transform = dred.transform
                nsample = 2000
                red = dred.read(1, out_shape=(nsample, nsample)).astype("float32")
                nir = dnir.read(1, out_shape=(nsample, nsample)).astype("float32")
            red *= 0.0001
            nir *= 0.0001
            denom = nir + red
            ndvi = np.where(denom > 1e-6, (nir - red) / np.maximum(denom, 1e-6), np.nan)
            ndvi[(red <= 0) | (nir <= 0)] = np.nan
            reproject(
                source=ndvi, destination=stack[k],
                src_transform=src_transform, src_crs=src_crs,
                dst_transform=dst_transform, dst_crs="EPSG:4326",
                resampling=Resampling.bilinear, dst_nodata=np.nan,
            )
            escenas_ok += 1
        except Exception as exc:  # noqa: BLE001
            _log(f"⚠️ escena Sentinel-2 omitida: {exc}")

    if escenas_ok == 0:
        return None, None

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        ndvi_mosaic = np.nanmedian(stack, axis=0)

    np.savez_compressed(cache_f, ndvi=ndvi_mosaic, transform=np.array(tuple(dst_transform)))
    _log(f"NDVI: mosaico real {width}x{height} de {escenas_ok} escenas")
    return ndvi_mosaic, np.array(tuple(dst_transform))


def sample_ndvi(ndvi, transform, lons, lats):
    """Muestrea el mosaico NDVI para arreglos de lon/lat."""
    from rasterio.transform import Affine
    if ndvi is None:
        return np.full(len(lons), np.nan, "float32")
    tr = Affine(*np.asarray(transform, float)[:6])
    cols, rows = ~tr * (np.asarray(lons, float), np.asarray(lats, float))
    cols = np.round(cols).astype(int)
    rows = np.round(rows).astype(int)
    out = np.full(len(lons), np.nan, "float32")
    ok = (rows >= 0) & (rows < ndvi.shape[0]) & (cols >= 0) & (cols < ndvi.shape[1])
    out[ok] = ndvi[rows[ok], cols[ok]]
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 4) DISTANCIAS REALES A VÍAS Y POBLADOS — OpenStreetMap (Overpass)
# ─────────────────────────────────────────────────────────────────────────────

_OVERPASS = "https://overpass-api.de/api/interpreter"
_VIAS = "motorway|trunk|primary|secondary|tertiary|unclassified|residential"


def _overpass(query):
    r = requests.post(_OVERPASS, data={"data": query}, headers=UA, timeout=180)
    r.raise_for_status()
    return r.json()


def fetch_osm_vectors(bbox):
    """Descarga vías y localidades reales de OSM para el bbox."""
    cache_f = CACHE / "osm_vectors.npz"
    if cache_f.exists():
        z = np.load(cache_f, allow_pickle=True)
        _log("OSM: caché de vectores")
        return z["vias"].tolist(), z["poblados"].tolist()

    min_lat, min_lon, max_lat, max_lon = bbox
    s, w, n, e = min_lat, min_lon, max_lat, max_lon

    vias = []
    q_vias = (f'[out:json][timeout:180];'
              f'way["highway"~"{_VIAS}"]({s},{w},{n},{e});out geom;')
    try:
        for el in _overpass(q_vias).get("elements", []):
            geom = el.get("geometry")
            if geom and len(geom) >= 2:
                vias.append([(pt["lon"], pt["lat"]) for pt in geom])
    except Exception as exc:  # noqa: BLE001
        _log(f"⚠️ Overpass vías: {exc}")

    poblados = []
    q_pob = (f'[out:json][timeout:120];'
             f'node["place"~"city|town|village"]({s},{w},{n},{e});out;')
    try:
        for el in _overpass(q_pob).get("elements", []):
            if "lat" in el and "lon" in el:
                poblados.append((el["lon"], el["lat"]))
    except Exception as exc:  # noqa: BLE001
        _log(f"⚠️ Overpass poblados: {exc}")

    np.savez_compressed(cache_f, vias=np.array(vias, dtype=object),
                        poblados=np.array(poblados, dtype=object))
    _log(f"OSM: {len(vias)} vías y {len(poblados)} poblados reales")
    return vias, poblados


def compute_osm_distances(grid, vias, poblados):
    """Distancia (m) de cada celda a la vía y al poblado más cercanos."""
    import geopandas as gpd
    from shapely.geometry import LineString, Point

    g = grid[["grid_id", "longitude", "latitude"]].copy()
    pts = gpd.GeoDataFrame(
        g, geometry=gpd.points_from_xy(g["longitude"], g["latitude"]), crs="EPSG:4326"
    ).to_crs("EPSG:32717")

    dist_road = np.full(len(g), np.nan)
    dist_town = np.full(len(g), np.nan)

    if vias:
        roads = gpd.GeoDataFrame(
            geometry=[LineString(v) for v in vias], crs="EPSG:4326"
        ).to_crs("EPSG:32717")
        near = gpd.sjoin_nearest(pts, roads[["geometry"]], how="left", distance_col="d")
        near = near[~near.index.duplicated(keep="first")]
        dist_road = near["d"].reindex(pts.index).to_numpy()

    if poblados:
        towns = gpd.GeoDataFrame(
            geometry=[Point(p) for p in poblados], crs="EPSG:4326"
        ).to_crs("EPSG:32717")
        near = gpd.sjoin_nearest(pts, towns[["geometry"]], how="left", distance_col="d")
        near = near[~near.index.duplicated(keep="first")]
        dist_town = near["d"].reindex(pts.index).to_numpy()

    return dist_road, dist_town


# ─────────────────────────────────────────────────────────────────────────────
# Orquestador
# ─────────────────────────────────────────────────────────────────────────────

def attach_real_features(grid, bbox, ref_date, start, end):
    """Calcula y añade TODAS las features reales a la grilla (GeoDataFrame)."""
    import geopandas as gpd  # noqa: F401
    from scipy.spatial import cKDTree

    lons = grid["longitude"].to_numpy(float)
    lats = grid["latitude"].to_numpy(float)

    # 1) Meteo ERA5 (nearest al punto de rejilla)
    meteo = fetch_meteo(bbox, ref_date)
    if not meteo.empty:
        tree = cKDTree(meteo[["longitude", "latitude"]].to_numpy())
        _, idx = tree.query(np.column_stack([lons, lats]))
        for col in ["temp_2m", "humedad_relativa", "viento_velocidad", "viento_direccion",
                    "dias_sin_lluvia", "lluvia_acum_7d", "lluvia_acum_15d",
                    "temp_lag1", "humedad_lag1"]:
            grid[col] = meteo[col].to_numpy()[idx]

    # 2) Pendiente / aspecto / elevación (DEM real)
    dem = build_dem_layer(bbox)
    elev, slope, aspect = sample_dem(dem, lons, lats)
    grid["elevacion_m"] = np.round(elev, 1)
    grid["pendiente_pct"] = np.round(np.clip(slope, 0.5, 90.0), 2)
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    grid["orientacion"] = [dirs[int((a % 360) // 45) % 8] if not np.isnan(a) else "N" for a in aspect]

    # 3) NDVI real (Sentinel-2)
    ndvi, transform = fetch_ndvi_mosaic(bbox, start, end)
    grid["ndvi"] = np.round(np.clip(sample_ndvi(ndvi, transform, lons, lats), 0.02, 0.95), 3)

    # 4) Distancias reales (OSM)
    vias, poblados = fetch_osm_vectors(bbox)
    d_road, d_town = compute_osm_distances(grid, vias, poblados)
    grid["dist_carretera_m"] = np.round(d_road, 1)
    grid["dist_poblado_m"] = np.round(d_town, 1)

    return grid


if __name__ == "__main__":
    bbox = (-7.7592, -79.4517, -4.5519, -77.7389)
    start, end, ref = "2026-08-15", "2026-09-06", "2026-09-06"
    print("Probando fuentes reales...")
    meteo = fetch_meteo(bbox, ref)
    print(meteo.head().to_string())
    dem = build_dem_layer(bbox)
    print("teselas DEM:", len(dem))
    ndvi, tr = fetch_ndvi_mosaic(bbox, start, end)
    print("NDVI mosaic:", None if ndvi is None else ndvi.shape)
    vias, poblados = fetch_osm_vectors(bbox)
    print("vias:", len(vias), "poblados:", len(poblados))
    print("OK")
