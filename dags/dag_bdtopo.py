"""DAG Airflow — BD TOPO IGN (routes, haies, végétation, bâtiments)."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
import subprocess
import os

PG_CONN = "postgresql://eolien:eolien123@postgis:5432/eolien_db"
IGN_API = "https://data.geopf.fr/wfs/ows"

LAYERS = {
    "ROUTE_PRIMAIRE": "raw.bdtopo_routes",
    "HAIE": "raw.bdtopo_haies",
    "ZONE_DE_VEGETATION": "raw.bdtopo_vegetation",
    "BATIMENT": "raw.bdtopo_batiments",
    "LIGNE_ELECTRIQUE": "raw.bdtopo_lignes_elec",
    "PYLONE": "raw.bdtopo_pylones",
}

default_args = {
    "owner": "eolien-pipeline",
    "retries": 2,
    "retry_delay": timedelta(minutes=15),
    "email_on_failure": False,
}


def load_wfs_layer(layer_name: str, pg_table: str, **_) -> None:
    wfs_url = (
        f"WFS:{IGN_API}?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature"
        f"&TYPENAMES=BDTOPO_V3:{layer_name}&SRSNAME=EPSG:2154"
    )
    cmd = [
        "ogr2ogr",
        "-f", "PostgreSQL",
        f"PG:{PG_CONN}",
        wfs_url,
        "-nln", pg_table,
        "-lco", "GEOMETRY_NAME=geometry",
        "-lco", "FID=gid",
        "-overwrite",
        "-progress",
        "-t_srs", "EPSG:2154",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if result.returncode != 0:
        raise RuntimeError(f"ogr2ogr failed for {layer_name}: {result.stderr}")


with DAG(
    dag_id="dag_bdtopo_ign",
    default_args=default_args,
    description="Ingestion BD TOPO IGN via WFS (6 couches)",
    schedule_interval="0 3 1 */3 *",  # trimestriel
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["bdtopo", "ign", "ingestion"],
) as dag:

    create_schema = BashOperator(
        task_id="create_schema_raw",
        bash_command='psql "$PG_CONN" -c "CREATE SCHEMA IF NOT EXISTS raw;"',
        env={"PG_CONN": PG_CONN},
    )

    for layer, table in LAYERS.items():
        task = PythonOperator(
            task_id=f"load_{layer.lower()}",
            python_callable=load_wfs_layer,
            op_kwargs={"layer_name": layer, "pg_table": table},
        )
        create_schema >> task
