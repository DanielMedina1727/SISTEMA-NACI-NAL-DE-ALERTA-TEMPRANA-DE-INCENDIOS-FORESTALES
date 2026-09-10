"""
Motor de propagación por viento (el "diferencial" del proyecto, Semana 9-12).

Idea: si una grilla está en Rojo y el viento sopla hacia el NE, las grillas
vecinas en esa dirección reciben un nivel Amarillo (riesgo de recibir
cenizas/fuego), con probabilidad decreciente según distancia.
"""
import math

# Vecinos relativos en una grilla de 8 direcciones (fila, columna)
DIRECTIONS = {
    "N": (0, 1), "NE": (1, 1), "E": (1, 0), "SE": (1, -1),
    "S": (0, -1), "SW": (-1, -1), "W": (-1, 0), "NW": (-1, 1),
}


def wind_degrees_to_compass(degrees: float) -> str:
    """Convierte grados (0-360, 0=Norte) a una de las 8 direcciones cardinales."""
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = round(degrees / 45) % 8
    return dirs[idx]


def parse_grid_id(grid_id: str) -> tuple[float, float]:
    lon_str, lat_str = grid_id.split("_")
    return float(lon_str), float(lat_str)


def propagate_risk(grid_id: str, viento_direccion: float, viento_velocidad: float,
                    cell_size: float = 0.009, n_cells: int = 3) -> dict:
    """
    Dado el ID de una grilla en Rojo, calcula las N grillas vecinas en la dirección
    del viento y les asigna un nivel Amarillo con probabilidad decreciente.
    """
    compass = wind_degrees_to_compass(viento_direccion)
    d_lon, d_lat = DIRECTIONS[compass]
    lon, lat = parse_grid_id(grid_id)

    # A mayor velocidad del viento, mayor alcance de la propagación (ejemplo simple;
    # ajusta la función según literatura de modelos de propagación tipo Rothermel
    # si quieres mayor rigor físico).
    reach = min(n_cells, max(1, int(viento_velocidad // 5)))

    affected = []
    for step in range(1, reach + 1):
        neighbor_lon = lon + d_lon * cell_size * step
        neighbor_lat = lat + d_lat * cell_size * step
        neighbor_id = f"{neighbor_lon:.4f}_{neighbor_lat:.4f}"
        probabilidad = max(0.1, 0.6 * math.exp(-0.5 * step))  # decae con la distancia
        affected.append({
            "grid_id": neighbor_id,
            "nivel": "Amarillo",
            "probabilidad_recibir_fuego": round(probabilidad, 2),
        })

    return {
        "origen": grid_id,
        "direccion_viento": compass,
        "velocidad_viento": viento_velocidad,
        "grillas_afectadas": affected,
    }
