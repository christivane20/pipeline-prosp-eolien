"""Chargement des données géospatiales dans PostGIS via ogr2ogr / GeoPandas.

Usage:
    python scripts/02_load_postgis.py --source cadastre --dept 60
    python scripts/02_load_postgis.py --source sia
    python scripts/02_load_postgis.py --source all
"""
import argparse
import subprocess
import os
from pathlib import Path
import geopandas as gpd
from sqlalchemy import create_engine, text

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5433")
PG_DB = os.getenv("PG_DB", "eolien_db")
PG_USER = os.getenv("PG_USER", "eolien")
PG_PASS = os.getenv("PG_PASS", "eolien123")

PG_CONN = f"postgresql+psycopg://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"
PG_OGR = f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"

DATA_DIR = Path("data/raw")
TARGET_EPSG = 2154


def get_engine():
    return create_engine(PG_CONN)


def ensure_schema(schema: str = "raw") -> None:
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()


def load_geospatial(filepath: Path, table: str, schema: str = "raw", if_exists: str = "replace") -> None:
    print(f"Chargement {filepath} → {schema}.{table}")
    gdf = gpd.read_file(str(filepath))
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    gdf = gdf.to_crs(epsg=TARGET_EPSG)
    engine = get_engine()
    gdf.to_postgis(table, engine, schema=schema, if_exists=if_exists, index=False)
    print(f"  {len(gdf)} entités chargées")


def load_via_ogr2ogr(filepath: Path, table: str, schema: str = "raw") -> None:
    """Utilise ogr2ogr pour les fichiers volumineux ou formats complexes (GDB, DXF...)."""
    cmd = [
        "ogr2ogr",
        "-f", "PostgreSQL",
        f"PG:{PG_OGR} active_schema={schema}",
        str(filepath),
        "-nln", table,
        "-lco", "GEOMETRY_NAME=geometry",
        "-lco", "FID=gid",
        "-overwrite",
        "-progress",
        "-t_srs", f"EPSG:{TARGET_EPSG}",
        "-skipfailures",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if result.returncode != 0:
        raise RuntimeError(f"ogr2ogr failed: {result.stderr[-500:]}")
    print(f"  ogr2ogr OK → {schema}.{table}")


LOAD_MAP = {
    "cadastre": lambda dept: load_geospatial(DATA_DIR / f"cadastre_{dept}.geojson", f"cadastre_parcelles_{dept}"),
    "sia": lambda _: load_via_ogr2ogr(DATA_DIR / "sia", "sia_obstacles"),
    "zaer": lambda _: load_geospatial(DATA_DIR / "zaer.geojson", "zaer_proposees"),
    "zaer_arretees": lambda _: load_geospatial(DATA_DIR / "zaer_arretees.geojson", "zaer_arretees"),
    "monuments_histo": lambda _: load_geospatial(DATA_DIR / "monuments_histo.geojson", "mcc_monuments_historiques"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Chargement données SIG → PostGIS")
    parser.add_argument("--source", required=True, choices=[*LOAD_MAP.keys(), "all"])
    parser.add_argument("--dept", help="Code département (pour source=cadastre)")
    args = parser.parse_args()

    ensure_schema("raw")

    if args.source == "all":
        for src, fn in LOAD_MAP.items():
            if src == "cadastre" and not args.dept:
                print(f"[{src}] Ignoré (--dept requis)")
                continue
            fn(args.dept)
    else:
        LOAD_MAP[args.source](args.dept)


if __name__ == "__main__":
    main()
