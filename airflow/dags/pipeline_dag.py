"""
DAG de Airflow que orquesta el pipeline diario del Sistema Nacional de Alerta
Temprana de Incendios Forestales:

  1. Descarga los focos de calor reales de NASA FIRMS (etiquetas del modelo).
  2. Reconstruye la grilla de features reales (DEM + Sentinel-2 + ERA5 + OSM).
  3. Reentrena el ensemble con validación espacial out-of-fold.
  4. Puntúa la grilla del día y exporta el GeoJSON de riesgo.
  5. Envía el resumen diario de alertas por WhatsApp (app/scheduler.py).

Copia este archivo a la carpeta `dags/` de tu instalación de Airflow:
    cp airflow/dags/pipeline_dag.py $AIRFLOW_HOME/dags/

Requiere:
  - Las variables de entorno del proyecto (.env) accesibles por el worker.
  - FIRMS_MAP_KEY configurada para el paso de descarga.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

CAJAMARCA_BBOX = "-79.4517,-7.7592,-77.7389,-4.5519"
DATA_DIR = "/opt/airflow/data"

default_args = {
    "owner": "wildfire-team",
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}


def task_fetch_firms():
    """Descarga los focos de calor reales de NASA FIRMS (últimos 3 días)."""
    from data_pipeline.fetch_firms import fetch_firms_area

    df = fetch_firms_area(CAJAMARCA_BBOX, days=3)
    df.to_csv(f"{DATA_DIR}/firms_raw.csv", index=False)
    print(f"Focos descargados: {len(df)}")
    return len(df)


def task_build_grid():
    """Regenera la grilla de features reales por celda de 1 km²."""
    import subprocess
    import sys

    subprocess.run(
        [
            sys.executable,
            "data_pipeline/grid_builder.py",
            "--bbox", *CAJAMARCA_BBOX.split(","),
            "--out", f"{DATA_DIR}/dataset.parquet",
        ],
        check=True,
    )


def task_train_model():
    """Reentrena el ensemble con validación cruzada espacial (out-of-fold)."""
    import subprocess
    import sys

    subprocess.run([sys.executable, "data_pipeline/train_model.py"], check=True)


def task_score_and_export():
    """Puntúa la grilla del día y exporta el GeoJSON de riesgo."""
    import json

    from app.main import risk_today

    geo = risk_today(limit=5000)
    with open(f"{DATA_DIR}/risk_today.geojson", "w", encoding="utf-8") as fh:
        json.dump(geo, fh, ensure_ascii=False)
    stats = geo.get("stats", {})
    print(f"Riesgo exportado. Stats: {stats}")
    return stats


def task_send_daily_alerts():
    """Envía el resumen diario de riesgo a los grupos de WhatsApp configurados."""
    import asyncio

    from app.scheduler import run_daily_alerts

    asyncio.run(run_daily_alerts())


with DAG(
    dag_id="wildfire_daily_pipeline",
    default_args=default_args,
    description="Descarga datos, reentrena, predice riesgo y envía alertas diariamente",
    schedule="0 7 * * *",  # todos los días a las 07:00 (America/Lima)
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["wildfire", "capstone"],
) as dag:

    fetch_firms = PythonOperator(task_id="fetch_firms", python_callable=task_fetch_firms)
    build_grid = PythonOperator(task_id="build_grid", python_callable=task_build_grid)
    train_model = PythonOperator(task_id="train_model", python_callable=task_train_model)
    score_export = PythonOperator(task_id="score_and_export", python_callable=task_score_and_export)
    send_alerts = PythonOperator(task_id="send_daily_alerts", python_callable=task_send_daily_alerts)

    fetch_firms >> build_grid >> train_model >> score_export >> send_alerts
