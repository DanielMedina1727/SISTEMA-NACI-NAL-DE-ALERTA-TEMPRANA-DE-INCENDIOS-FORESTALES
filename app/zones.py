"""Zonas operativas y variables de entorno asociadas a sus grupos de WhatsApp.

Se mantiene en un módulo independiente para que el scheduler y el módulo de
alertas usen exactamente el mismo orden al repartir grupos entre instancias.
"""

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

ZONE_GROUP_ENV_KEYS = [zona["env_key"] for zona in ZONAS]


def _distance_to_center_sq(lat: float, lon: float, zona: dict) -> float:
    """Distancia cuadrada al centro del bbox (suficiente para comparar)."""
    center_lat = (zona["lat_min"] + zona["lat_max"]) / 2
    center_lon = (zona["lon_min"] + zona["lon_max"]) / 2
    return (lat - center_lat) ** 2 + (lon - center_lon) ** 2


def find_zone_for_point(lat: float, lon: float) -> dict | None:
    """Devuelve la zona cuyo bbox contiene el punto.

    Si el punto cae en el cruce de dos zonas, se elige la de centro más cercano.
    Si está fuera de todas, devuelve None (no se envía a un grupo equivocado).
    """
    matches = [
        zona
        for zona in ZONAS
        if zona["lat_min"] <= lat <= zona["lat_max"]
        and zona["lon_min"] <= lon <= zona["lon_max"]
    ]
    if not matches:
        return None
    return min(matches, key=lambda zona: _distance_to_center_sq(lat, lon, zona))

