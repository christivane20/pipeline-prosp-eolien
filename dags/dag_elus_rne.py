"""DAG Airflow — Élus RNE (Répertoire National des Élus) via API gouvernementale."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import requests
import pandas as pd
from sqlalchemy import create_engine

PG_CONN = "postgresql+psycopg://eolien:eolien123@postgis:5432/eolien_db"

# API Données.gouv.fr — élus communaux, départementaux, régionaux
RNE_DATASETS = {
    "conseillers_municipaux": "https://www.data.gouv.fr/fr/datasets/r/d5f400de-ae3f-4966-8cb6-a85c70c6c24a",
    "conseillers_departementaux": "https://www.data.gouv.fr/fr/datasets/r/601ef073-d986-4582-8e1a-ed14dc857fba",
    "conseillers_regionaux": "https://www.data.gouv.fr/fr/datasets/r/430e13f9-834b-4411-a1a8-da0b4b6e715c",
}

default_args = {
    "owner": "eolien-pipeline",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


def download_rne(dataset_key: str, url: str, **_) -> None:
    resp = requests.get(url, timeout=180)
    resp.raise_for_status()
    from io import StringIO
    df = pd.read_csv(StringIO(resp.text), sep=";", dtype=str, encoding="utf-8")
    df.columns = [c.lower().replace(" ", "_").replace("é", "e").replace("è", "e") for c in df.columns]
    engine = create_engine(PG_CONN)
    df.to_sql(f"rne_{dataset_key}", engine, schema="raw", if_exists="replace", index=False)


def build_contacts_eolien(**_) -> None:
    """Croise élus communaux avec les communes du projet (table contacts_maire)."""
    engine = create_engine(PG_CONN)
    sql = """
    INSERT INTO raw.contacts_projet_elus
    SELECT DISTINCT
        e.nom,
        e.prenom,
        e.libelle_de_la_commune,
        e.code_de_la_commune,
        e.libelle_du_departement,
        e.profession,
        'maire' AS fonction
    FROM raw.rne_conseillers_municipaux e
    JOIN raw.communes_projet p
        ON e.code_de_la_commune = p.insee_com
    WHERE e.libelle_de_la_fonction ILIKE '%%maire%%'
    ON CONFLICT DO NOTHING;
    """
    with engine.connect() as conn:
        conn.execute(sql)
        conn.commit()


with DAG(
    dag_id="dag_elus_rne",
    default_args=default_args,
    description="Mise à jour mensuelle des élus RNE — contacts prospection",
    schedule_interval="0 6 1 * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["rne", "elus", "administratif", "ingestion"],
) as dag:

    tasks_dl = []
    for key, url in RNE_DATASETS.items():
        t = PythonOperator(
            task_id=f"download_rne_{key}",
            python_callable=download_rne,
            op_kwargs={"dataset_key": key, "url": url},
        )
        tasks_dl.append(t)

    t_contacts = PythonOperator(
        task_id="build_contacts_eolien",
        python_callable=build_contacts_eolien,
    )

    tasks_dl >> t_contacts
