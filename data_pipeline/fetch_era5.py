"""
Descarga variables atmosféricas de ERA5 (Copernicus Climate Data Store):
viento (u/v a 10m), temperatura a 2m y humedad relativa.

Requiere `pip install cdsapi` y credenciales en ~/.cdsapirc o en .env
(CDS_API_URL, CDS_API_KEY) — regístrate gratis en https://cds.climate.copernicus.eu/

Uso:
    python fetch_era5.py --area PERU --year 2023 --month 08 --out data/era5_raw.nc
"""
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Bounding boxes de ejemplo [Norte, Oeste, Sur, Este]
AREAS = {
    "PERU": [0.0, -81.5, -18.5, -68.5],
    "CAJAMARCA": [-4.5, -79.5, -7.5, -77.5],
}


def fetch_era5(area_name: str, year: str, month: str, out_path: str):
    import cdsapi  # import diferido: solo se necesita si se ejecuta esta función

    client = cdsapi.Client(
        url=os.getenv("CDS_API_URL"),
        key=os.getenv("CDS_API_KEY"),
    )

    area = AREAS.get(area_name.upper())
    if area is None:
        raise ValueError(f"Área '{area_name}' no definida. Opciones: {list(AREAS)}")

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    client.retrieve(
        "reanalysis-era5-single-levels",
        {
            "product_type": "reanalysis",
            "variable": [
                "10m_u_component_of_wind",
                "10m_v_component_of_wind",
                "2m_temperature",
                "2m_dewpoint_temperature",  # usado para derivar humedad relativa
            ],
            "year": year,
            "month": month,
            "day": [f"{d:02d}" for d in range(1, 32)],
            "time": [f"{h:02d}:00" for h in range(0, 24, 6)],  # cada 6 horas
            "area": area,
            "format": "netcdf",
        },
        out_path,
    )
    print(f"✅ Datos ERA5 guardados en {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Descarga variables ERA5 de Copernicus")
    parser.add_argument("--area", default="PERU", choices=list(AREAS.keys()))
    parser.add_argument("--year", required=True)
    parser.add_argument("--month", required=True, help="Formato MM (ej: 08)")
    parser.add_argument("--out", default="data/era5_raw.nc")
    args = parser.parse_args()

    fetch_era5(args.area, args.year, args.month, args.out)


if __name__ == "__main__":
    main()
