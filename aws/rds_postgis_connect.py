"""Connexion et gestion de l'instance RDS PostGIS managée (AWS).

Fournit un helper de connexion utilisable par tous les scripts du pipeline.

Usage:
    from aws.rds_postgis_connect import get_engine, get_rds_connection_string
    engine = get_engine()
"""
import os
import boto3
from sqlalchemy import create_engine, Engine, text


def _get_rds_password() -> str:
    """Récupère le mot de passe RDS depuis AWS Secrets Manager."""
    secret_name = os.getenv("RDS_SECRET_NAME", "eolien/rds/postgis")
    region = os.getenv("AWS_REGION", "eu-west-3")
    client = boto3.client("secretsmanager", region_name=region)
    resp = client.get_secret_value(SecretId=secret_name)
    import json
    secret = json.loads(resp["SecretString"])
    return secret["password"]


def get_rds_connection_string(use_secrets_manager: bool = True) -> str:
    host = os.environ["RDS_HOST"]
    port = os.getenv("RDS_PORT", "5432")
    db = os.getenv("RDS_DB", "eolien_db")
    user = os.getenv("RDS_USER", "eolien_admin")
    if use_secrets_manager:
        password = _get_rds_password()
    else:
        password = os.environ["RDS_PASS"]
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


def get_engine(use_secrets_manager: bool = True, **kwargs) -> Engine:
    conn_str = get_rds_connection_string(use_secrets_manager)
    return create_engine(conn_str, pool_pre_ping=True, **kwargs)


def check_connection() -> bool:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            version = conn.execute(text("SELECT PostGIS_Version()")).scalar()
        print(f"RDS PostGIS connecté — version : {version[:30]}")
        return True
    except Exception as exc:
        print(f"Connexion RDS échouée : {exc}")
        return False


def get_local_engine() -> Engine:
    """Moteur local (Docker) pour les tests hors AWS."""
    conn = (
        f"postgresql+psycopg://{os.getenv('PG_USER','eolien')}:"
        f"{os.getenv('PG_PASS','eolien123')}@"
        f"{os.getenv('PG_HOST','localhost')}:"
        f"{os.getenv('PG_PORT','5433')}/"
        f"{os.getenv('PG_DB','eolien_db')}"
    )
    return create_engine(conn, pool_pre_ping=True)


if __name__ == "__main__":
    import sys
    env = os.getenv("PIPELINE_ENV", "local")
    if env == "aws":
        ok = check_connection()
    else:
        engine = get_local_engine()
        with engine.connect() as conn:
            v = conn.execute(text("SELECT PostGIS_Version()")).scalar()
        print(f"PostGIS local OK : {v[:30]}")
        ok = True
    sys.exit(0 if ok else 1)
