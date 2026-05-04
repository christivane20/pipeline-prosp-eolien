"""API géospatiale REST — pipeline SIG éolien.

Lancement:
    uvicorn scripts.04_api_fastapi:app --reload --port 8000

Endpoints:
    GET /health
    GET /communes/{insee}
    GET /zaer?bbox=...
    GET /eoliennes?dept=...
    GET /contraintes/{insee}
    POST /analyse-ia
"""
import os
from typing import Annotated

from fastapi import FastAPI, Query, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import geopandas as gpd
from sqlalchemy import create_engine, text

PG_CONN = (
    f"postgresql+psycopg://{os.getenv('PG_USER','eolien')}:{os.getenv('PG_PASS','eolien123')}"
    f"@{os.getenv('PG_HOST','localhost')}:{os.getenv('PG_PORT','5433')}/{os.getenv('PG_DB','eolien_db')}"
)

app = FastAPI(
    title="API SIG Éolien",
    description="API géospatiale REST — pipeline prospection éolienne onshore",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def get_engine():
    return create_engine(PG_CONN)


@app.get("/health")
def health():
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/communes/{insee}")
def get_commune(insee: Annotated[str, Path(description="Code INSEE commune (5 chiffres)")]):
    sql = "SELECT * FROM mart.communes_projet WHERE insee_com = :insee LIMIT 1"
    with get_engine().connect() as conn:
        row = conn.execute(text(sql), {"insee": insee}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Commune {insee} non trouvée")
    return dict(row)


@app.get("/zaer")
def get_zaer(
    dept: Annotated[str | None, Query(description="Filtre par département (ex: 60)")] = None,
    statut: Annotated[str | None, Query(description="proposee | arretee")] = None,
):
    sql = "SELECT * FROM mart.zaer_coverage WHERE 1=1"
    params: dict = {}
    if dept:
        sql += " AND LEFT(insee_com, 2) = :dept"
        params["dept"] = dept
    if statut == "arretee":
        sql = sql.replace("mart.zaer_coverage", "raw.zaer_arretees")
    gdf = gpd.read_postgis(sql, get_engine(), geom_col="geometry", params=params)
    return gdf.__geo_interface__


@app.get("/eoliennes")
def get_eoliennes(
    dept: Annotated[str | None, Query(description="Code département")] = None,
    statut: Annotated[str | None, Query(description="Filtre statut (autorisé, construit...)")] = None,
):
    sql = "SELECT * FROM mart.eoliennes WHERE 1=1"
    params: dict = {}
    if dept:
        sql += " AND dept = :dept"
        params["dept"] = dept
    if statut:
        sql += " AND statut ILIKE :statut"
        params["statut"] = f"%{statut}%"
    gdf = gpd.read_postgis(sql, get_engine(), geom_col="geometry", params=params)
    return gdf.__geo_interface__


@app.get("/contraintes/{insee}")
def get_contraintes(insee: Annotated[str, Path(description="Code INSEE commune")]):
    sql = """
    SELECT type_contrainte, rayon_eloignement_m,
           ST_AsGeoJSON(geometry)::json AS geom
    FROM mart.contraintes_paysage
    WHERE ST_DWithin(
        geometry,
        (SELECT ST_Centroid(geometry) FROM mart.communes_projet WHERE insee_com = :insee),
        50000
    )
    """
    with get_engine().connect() as conn:
        rows = conn.execute(text(sql), {"insee": insee}).mappings().all()
    return {"insee": insee, "contraintes": [dict(r) for r in rows]}


class AnalyseRequest(BaseModel):
    insee: str
    rayon_km: float = 20.0


@app.post("/analyse-ia")
async def analyse_ia(req: AnalyseRequest):
    import anthropic
    contraintes = get_contraintes(req.insee)
    nb = len(contraintes["contraintes"])
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": (
                f"Commune INSEE {req.insee} — rayon d'analyse {req.rayon_km} km.\n"
                f"{nb} contraintes paysagères identifiées : {contraintes['contraintes'][:5]}.\n"
                "Donne une analyse concise de la faisabilité éolienne et des points de vigilance."
            ),
        }],
    )
    return {"insee": req.insee, "analyse": response.content[0].text}
