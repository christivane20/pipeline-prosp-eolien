"""DAG Airflow — Cadastre DGFiP (×95 départements)."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import requests
import geopandas as gpd
from sqlalchemy import create_engine

DEPTS = [str(d).zfill(2) for d in range(1, 96) if d != 20] + ["2A", "2B"]
PG_CONN = "postgresql+psycopg://eolien:eolien123@postgis:5432/eolien_db"
BASE_URL = "https://cadastre.data.gouv.fr/bundler/cadastre-etalab/departements/{dept}/geojson/parcelles"

default_args = {
    "owner": "eolien-pipeline",
    "retries": 3,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}


def download_dept(dept: str, **ctx) -> str:
    url = BASE_URL.format(dept=dept)
    resp = requests.get(url, timeout=300, stream=True)
    resp.raise_for_status()
    path = f"/tmp/cadastre_{dept}.geojson"
    with open(path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    ctx["ti"].xcom_push(key="filepath", value=path)
    return path


def load_postgis(dept: str, **ctx) -> None:
    path = ctx["ti"].xcom_pull(key="filepath", task_ids=f"download_{dept}")
    engine = create_engine(PG_CONN)
    gdf = gpd.read_file(path)
    gdf = gdf.to_crs(epsg=2154)
    gdf["dept"] = dept
    gdf.to_postgis(
        "cadastre_parcelles",
        engine,
        if_exists="append",
        index=False,
        schema="raw",
    )


with DAG(
    dag_id="dag_cadastre_dgfip",
    default_args=default_args,
    description="Ingestion Cadastre DGFiP — 95 départements",
    schedule_interval="0 2 1 * *",  # 1er du mois à 2h
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["cadastre", "foncier", "ingestion"],
    max_active_tasks=5,
) as dag:

    create_schema = BashOperator(
        task_id="create_schema_raw",
        bash_command=(
            'psql "$PG_CONN" -c "CREATE SCHEMA IF NOT EXISTS raw;" '
            '-c "CREATE TABLE IF NOT EXISTS raw.cadastre_parcelles '
            '(id TEXT, geometry GEOMETRY(MULTIPOLYGON,2154), dept TEXT);"'
        ),
        env={"PG_CONN": PG_CONN.replace("postgresql+psycopg", "postgresql")},
    )

    for dept in DEPTS:
        t_dl = PythonOperator(
            task_id=f"download_{dept}",
            python_callable=download_dept,
            op_kwargs={"dept": dept},
        )
        t_load = PythonOperator(
            task_id=f"load_{dept}",
            python_callable=load_postgis,
            op_kwargs={"dept": dept},
        )
        create_schema >> t_dl >> t_load
