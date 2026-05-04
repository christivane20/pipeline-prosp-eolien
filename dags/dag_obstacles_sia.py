"""DAG Airflow — Obstacles aéronautiques SIA/DGAC + faisceaux ANFR."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import requests
import zipfile
import io
import geopandas as gpd
from sqlalchemy import create_engine

PG_CONN = "postgresql+psycopg://eolien:eolien123@postgis:5432/eolien_db"

# SIA publie les obstacles en SHP zippé trimestriellement
SIA_URL = "https://www.sia.aviation-civile.gouv.fr/dvd/espace_libraire/produits/produits_numeriques_non_aeronautiques/bdosa/BDOSA_SHP.zip"
ANFR_URL = "https://data.anfr.fr/api/explore/v2.1/catalog/datasets/observatoire_de_l_anfr_opendata/exports/geojson?where=type_support%3D%22FH%22"

default_args = {
    "owner": "eolien-pipeline",
    "retries": 3,
    "retry_delay": timedelta(minutes=20),
    "email_on_failure": False,
}


def load_sia_obstacles(**_) -> None:
    resp = requests.get(SIA_URL, timeout=600, stream=True)
    resp.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(resp.content))
    shp_files = [n for n in z.namelist() if n.endswith(".shp") and "OBSTACLE" in n.upper()]
    engine = create_engine(PG_CONN)
    gdfs = []
    for shp in shp_files:
        with z.open(shp) as f:
            gdf = gpd.read_file(f)
            gdfs.append(gdf)
    if gdfs:
        import pandas as pd
        merged = pd.concat(gdfs, ignore_index=True)
        merged = gpd.GeoDataFrame(merged, crs="EPSG:4326").to_crs(epsg=2154)
        merged.to_postgis("sia_obstacles", engine, schema="raw", if_exists="replace", index=False)


def load_anfr_faisceaux(**_) -> None:
    resp = requests.get(ANFR_URL, timeout=300)
    resp.raise_for_status()
    engine = create_engine(PG_CONN)
    gdf = gpd.read_file(io.BytesIO(resp.content))
    gdf = gdf.to_crs(epsg=2154)
    gdf.to_postgis("anfr_faisceaux_hertziens", engine, schema="raw", if_exists="replace", index=False)


with DAG(
    dag_id="dag_obstacles_sia_anfr",
    default_args=default_args,
    description="Obstacles SIA/DGAC + faisceaux hertziens ANFR",
    schedule_interval="0 1 1 */3 *",  # trimestriel
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["sia", "dgac", "anfr", "aviation", "ingestion"],
) as dag:

    t_sia = PythonOperator(
        task_id="load_sia_obstacles",
        python_callable=load_sia_obstacles,
        execution_timeout=timedelta(hours=2),
    )

    t_anfr = PythonOperator(
        task_id="load_anfr_faisceaux",
        python_callable=load_anfr_faisceaux,
    )

    [t_sia, t_anfr]
