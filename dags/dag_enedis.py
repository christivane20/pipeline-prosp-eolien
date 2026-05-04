"""DAG Airflow — Données réseau Enedis / Agence ORE."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import requests
import geopandas as gpd
from sqlalchemy import create_engine
import io

PG_CONN = "postgresql+psycopg://eolien:eolien123@postgis:5432/eolien_db"

ORE_SOURCES = {
    "postes_source": "https://opendata.agenceore.fr/api/explore/v2.1/catalog/datasets/postes-electriques-ht/exports/geojson",
    "raccordements": "https://opendata.agenceore.fr/api/explore/v2.1/catalog/datasets/capacites-daccueil/exports/geojson",
    "bilan_elec": "https://opendata.agenceore.fr/api/explore/v2.1/catalog/datasets/bilan-electrique-commune/exports/csv",
}

default_args = {
    "owner": "eolien-pipeline",
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}


def download_ore(source_key: str, url: str, **ctx) -> None:
    resp = requests.get(url, timeout=180)
    resp.raise_for_status()
    engine = create_engine(PG_CONN)
    if url.endswith("geojson"):
        gdf = gpd.read_file(io.BytesIO(resp.content))
        gdf = gdf.to_crs(epsg=2154)
        gdf.to_postgis(f"enedis_{source_key}", engine, schema="raw", if_exists="replace", index=False)
    else:
        import pandas as pd
        df = pd.read_csv(io.StringIO(resp.text), sep=";")
        df.to_sql(f"enedis_{source_key}", engine, schema="raw", if_exists="replace", index=False)


def download_rte_rao(**_) -> None:
    """Réseau Ouvert d'Accueil RTE — capacités de raccordement."""
    url = "https://opendata.reseaux-energies.fr/api/explore/v2.1/catalog/datasets/capacite-de-raccordement/exports/geojson"
    resp = requests.get(url, timeout=180)
    resp.raise_for_status()
    engine = create_engine(PG_CONN)
    gdf = gpd.read_file(io.BytesIO(resp.content))
    gdf = gdf.to_crs(epsg=2154)
    gdf.to_postgis("rte_raccordements", engine, schema="raw", if_exists="replace", index=False)


with DAG(
    dag_id="dag_enedis_ore",
    default_args=default_args,
    description="Ingestion Enedis / ORE / RTE réseau électrique",
    schedule_interval="0 4 1 * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["enedis", "rte", "reseau", "ingestion"],
) as dag:

    t_rte = PythonOperator(
        task_id="load_rte_raccordements",
        python_callable=download_rte_rao,
    )

    for key, url in ORE_SOURCES.items():
        PythonOperator(
            task_id=f"load_ore_{key}",
            python_callable=download_ore,
            op_kwargs={"source_key": key, "url": url},
        )

    t_rte
