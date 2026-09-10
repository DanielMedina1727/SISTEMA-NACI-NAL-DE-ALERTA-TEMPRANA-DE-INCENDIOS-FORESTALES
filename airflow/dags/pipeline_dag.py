"""
DAG de Airflow que orquesta la descarga diaria de datos y actualiza las
predicciones de riesgo. Copia este archivo a tu carpeta dags/ de Airflow.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "wildfire-team",
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}


def task_fetch_firms():
    from data_pipeline.fetch_firms import fetch_firms_country
    df = fetch_firms_country(country_code="PER", days=1)
    df.to_csv("/opt/data/firms_daily.csv", index=False)


def task_build_grid_and_predict():
    # TODO: cargar el CSV del día, correr grid_builder + model.predict_proba
    # y escribir el resultado en PostGIS (tabla risk_predictions).
    pass


def task_check_red_alerts():
    # TODO: consultar PostGIS por grillas nivel Rojo del día y llamar a
    # app.telegram_alerts.send_red_alert() para cada una.
    pass


with DAG(
    dag_id="wildfire_daily_pipeline",
    default_args=default_args,
    description="Descarga datos, predice riesgo y envía alertas diariamente",
    schedule_interval="0 6 * * *",  # todos los días a las 6am
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["wildfire", "capstone"],
) as dag:

    fetch_firms = PythonOperator(task_id="fetch_firms", python_callable=task_fetch_firms)
    build_and_predict = PythonOperator(task_id="build_grid_and_predict", python_callable=task_build_grid_and_predict)
    check_alerts = PythonOperator(task_id="check_red_alerts", python_callable=task_check_red_alerts)

    fetch_firms >> build_and_predict >> check_alerts
