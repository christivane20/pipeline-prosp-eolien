"""DAG Airflow — ZAER (Zones d'Accélération des Énergies Renouvelables)."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import requests
import geopandas as gpd
from sqlalchemy import create_engine
import io

PG_CONN = "postgresql+psycopg://eolien:eolien123@postgis:5432/eolien_db"

# ZAER proposées par les communes (délibérations)
ZAER_URL = "https://www.data.gouv.fr/fr/datasets/r/zones-acceleration-enr-communes.geojson"
# ZAER arrêtées par les préfets
ZAER_ARRETEES_URL = "https://www.data.gouv.fr/fr/datasets/r/zones-acceleration-enr-prefets.geojson"

default_args = {
    "owner": "eolien-pipeline",
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}


def load_zaer_communes(**_) -> None:
    resp = requests.get(ZAER_URL, timeout=300)
    resp.raise_for_status()
    engine = create_engine(PG_CONN)
    gdf = gpd.read_file(io.BytesIO(resp.content))
    gdf = gdf.to_crs(epsg=2154)
    gdf["source"] = "communes_deliberation"
    gdf.to_postgis("zaer_proposees", engine, schema="raw", if_exists="replace", index=False)


def load_zaer_arretees(**_) -> None:
    resp = requests.get(ZAER_ARRETEES_URL, timeout=300)
    resp.raise_for_status()
    engine = create_engine(PG_CONN)
    gdf = gpd.read_file(io.BytesIO(resp.content))
    gdf = gdf.to_crs(epsg=2154)
    gdf["source"] = "prefecture_arrete"
    gdf.to_postgis("zaer_arretees", engine, schema="raw", if_exists="replace", index=False)


def compute_coverage_stats(**_) -> None:
    """Calcule stats de couverture ZAER par commune."""
    engine = create_engine(PG_CONN)
    sql = """
    CREATE OR REPLACE VIEW mart.zaer_coverage AS
    SELECT
        z.insee_com,
        z.nom_commune,
        z.libelle_region,
        ST_Area(ST_Union(z.geometry)) / 10000 AS surface_zaer_ha,
        z.source
    FROM raw.zaer_arretees z
    GROUP BY z.insee_com, z.nom_commune, z.libelle_region, z.source;
    """
    with engine.connect() as conn:
        conn.execute(sql)
        conn.commit()


with DAG(
    dag_id="dag_zaer",
    default_args=default_args,
    description="Ingestion ZAER communes + ZAER arrêtées préfectures",
    schedule_interval="0 5 * * 1",  # hebdomadaire (lundi 5h)
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["zaer", "enr", "reglementaire", "ingestion"],
) as dag:

    t_communes = PythonOperator(
        task_id="load_zaer_communes",
        python_callable=load_zaer_communes,
    )

    t_arretees = PythonOperator(
        task_id="load_zaer_arretees",
        python_callable=load_zaer_arretees,
    )

    t_stats = PythonOperator(
        task_id="compute_coverage_stats",
        python_callable=compute_coverage_stats,
    )

    [t_communes, t_arretees] >> t_stats
