"""DAG Airflow — Monuments historiques et atlas des patrimoines (WFS MCC)."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import subprocess
import geopandas as gpd
from sqlalchemy import create_engine
import requests
import io

PG_CONN_OGR = "postgresql://eolien:eolien123@postgis:5432/eolien_db"
PG_CONN = "postgresql+psycopg://eolien:eolien123@postgis:5432/eolien_db"

WFS_MCC = "https://www.culture.gouv.fr/map/wfs"

LAYERS_MCC = {
    "monuments_historiques_classes": "MS:MONUMENTS_HISTORIQUES_CLASSES_P",
    "monuments_historiques_inscrits": "MS:MONUMENTS_HISTORIQUES_INSCRITS_P",
    "sites_classes": "MS:SITES_CLASSES",
    "sites_inscrits": "MS:SITES_INSCRITS",
    "secteurs_sauvegardes": "MS:SECTEURS_SAUVEGARDES",
}

ATLAS_URL = "https://data.culture.gouv.fr/api/explore/v2.1/catalog/datasets/atlas-des-patrimoines/exports/geojson"

default_args = {
    "owner": "eolien-pipeline",
    "retries": 2,
    "retry_delay": timedelta(minutes=15),
    "email_on_failure": False,
}


def load_wfs_mcc(layer_key: str, type_name: str, **_) -> None:
    cmd = [
        "ogr2ogr",
        "-f", "PostgreSQL",
        f"PG:{PG_CONN_OGR}",
        f"WFS:{WFS_MCC}?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES={type_name}&SRSNAME=EPSG:2154",
        "-nln", f"raw.mcc_{layer_key}",
        "-lco", "GEOMETRY_NAME=geometry",
        "-overwrite",
        "-t_srs", "EPSG:2154",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"ogr2ogr failed for {layer_key}: {result.stderr}")


def load_atlas_patrimoines(**_) -> None:
    resp = requests.get(ATLAS_URL, timeout=300)
    resp.raise_for_status()
    engine = create_engine(PG_CONN)
    gdf = gpd.read_file(io.BytesIO(resp.content))
    gdf = gdf.to_crs(epsg=2154)
    gdf.to_postgis("mcc_atlas_patrimoines", engine, schema="raw", if_exists="replace", index=False)


def build_contraintes_paysage(**_) -> None:
    engine = create_engine(PG_CONN)
    sql = """
    CREATE OR REPLACE VIEW mart.contraintes_paysage AS
    SELECT geometry, 'MH classé' AS type_contrainte, 500 AS rayon_eloignement_m FROM raw.mcc_monuments_historiques_classes
    UNION ALL
    SELECT geometry, 'MH inscrit', 500 FROM raw.mcc_monuments_historiques_inscrits
    UNION ALL
    SELECT geometry, 'Site classé', 0 FROM raw.mcc_sites_classes
    UNION ALL
    SELECT geometry, 'Site inscrit', 0 FROM raw.mcc_sites_inscrits;
    """
    with engine.connect() as conn:
        conn.execute(sql)
        conn.commit()


with DAG(
    dag_id="dag_monuments_histo",
    default_args=default_args,
    description="Ingestion Monuments historiques + Atlas patrimoines MCC",
    schedule_interval="0 3 1 */6 *",  # semestriel
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["patrimoine", "mcc", "paysage", "ingestion"],
) as dag:

    tasks_wfs = []
    for key, type_name in LAYERS_MCC.items():
        t = PythonOperator(
            task_id=f"load_mcc_{key}",
            python_callable=load_wfs_mcc,
            op_kwargs={"layer_key": key, "type_name": type_name},
        )
        tasks_wfs.append(t)

    t_atlas = PythonOperator(
        task_id="load_atlas_patrimoines",
        python_callable=load_atlas_patrimoines,
    )

    t_vue = PythonOperator(
        task_id="build_contraintes_paysage",
        python_callable=build_contraintes_paysage,
    )

    tasks_wfs >> t_atlas >> t_vue
