"""Analyse automatique de couches SIG éoliennes via Claude API (Anthropic).

Usage:
    python ml/claude_analysis.py --commune 60159
    python ml/claude_analysis.py --geojson data/sample/eoliennes_60.geojson
    python ml/claude_analysis.py --batch data/communes_projet.csv
"""
import argparse
import json
import os
from pathlib import Path

import anthropic
import geopandas as gpd
import pandas as pd

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1500

client = anthropic.Anthropic()


def analyser_commune(insee: str, pg_conn_str: str | None = None) -> dict:
    """Analyse IA complète d'une commune : contexte éolien, contraintes, ZAER."""
    context: dict = {"insee": insee}

    if pg_conn_str:
        from sqlalchemy import create_engine, text
        engine = create_engine(pg_conn_str)
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM mart.contexte_eolien WHERE insee_com = :insee"),
                {"insee": insee},
            ).mappings().first()
            if row:
                context["contexte_eolien"] = dict(row)

            contraintes = conn.execute(
                text("""
                SELECT type_contrainte, COUNT(*) AS nb, AVG(rayon_eloignement_m) AS rayon_m
                FROM mart.contraintes_enviro
                WHERE ST_DWithin(
                    geometry,
                    (SELECT ST_Centroid(geometry) FROM mart.communes_projet WHERE insee_com = :insee),
                    20000
                )
                GROUP BY type_contrainte
                """),
                {"insee": insee},
            ).mappings().all()
            context["contraintes"] = [dict(c) for c in contraintes]

    prompt = (
        f"Commune INSEE {insee} — Analyse de faisabilité éolienne.\n\n"
        f"Contexte :\n{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
        "Donne une analyse structurée avec :\n"
        "1. Résumé du contexte éolien local\n"
        "2. Principaux points de vigilance réglementaires\n"
        "3. Opportunités identifiées (ZAER, réseau, vent)\n"
        "4. Verdict de faisabilité (Favorable / Mitigé / Défavorable) avec justification\n"
        "5. Prochaines étapes recommandées pour le développeur"
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=(
            "Tu es un expert en développement éolien onshore en France (réglementation ICPE, "
            "contraintes SIG, procédures administratives). Tu analyses des données géospatiales "
            "pour guider la prospection foncière."
        ),
        messages=[{"role": "user", "content": prompt}],
    )

    return {
        "insee": insee,
        "context": context,
        "analyse": response.content[0].text,
        "tokens_used": response.usage.output_tokens,
    }


def analyser_geojson(geojson_path: str) -> str:
    """Analyse statistique d'un fichier GeoJSON de parcs éoliens."""
    gdf = gpd.read_file(geojson_path)
    stats: dict = {
        "nb_entites": len(gdf),
        "colonnes": list(gdf.columns.drop("geometry", errors="ignore")),
        "crs": str(gdf.crs),
    }
    for col in ["statut", "regime", "departement"]:
        if col in gdf.columns:
            stats[f"distribution_{col}"] = gdf[col].value_counts().head(10).to_dict()
    for col in ["puissance_nominale_mw", "nb_eoliennes", "hauteur_m"]:
        if col in gdf.columns:
            stats[f"stats_{col}"] = {
                "min": float(gdf[col].min()),
                "max": float(gdf[col].max()),
                "mean": round(float(gdf[col].mean()), 2),
                "sum": round(float(gdf[col].sum()), 2),
            }

    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": (
                f"Analyse ce dataset éolien ({Path(geojson_path).name}) "
                f"et identifie les tendances clés pour la prospection :\n"
                f"{json.dumps(stats, ensure_ascii=False, indent=2)}"
            ),
        }],
    )
    return response.content[0].text


def batch_analyse(csv_path: str, pg_conn_str: str | None = None, output_dir: str = "results/analyses") -> None:
    """Analyse en batch d'une liste de communes."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(csv_path, dtype=str)
    insees = df["insee_com"].tolist() if "insee_com" in df.columns else df.iloc[:, 0].tolist()

    results = []
    for i, insee in enumerate(insees, 1):
        print(f"[{i}/{len(insees)}] Analyse commune {insee}...")
        try:
            result = analyser_commune(insee, pg_conn_str)
            results.append(result)
            out_file = Path(output_dir) / f"analyse_{insee}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"  Erreur {insee}: {exc}")

    summary_path = Path(output_dir) / "batch_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({"nb_communes": len(results), "analyses": results}, f, ensure_ascii=False, indent=2)
    print(f"Batch terminé — {len(results)} communes analysées → {summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyse IA SIG éolien via Claude API")
    parser.add_argument("--commune", help="Code INSEE commune à analyser")
    parser.add_argument("--geojson", help="Fichier GeoJSON à analyser")
    parser.add_argument("--batch", help="CSV liste de communes (colonne insee_com)")
    parser.add_argument("--pg-conn", help="Chaîne connexion PostgreSQL (optionnel)", default=os.getenv("PG_CONN"))
    parser.add_argument("--output-dir", default="results/analyses")
    args = parser.parse_args()

    if args.commune:
        result = analyser_commune(args.commune, args.pg_conn)
        print(result["analyse"])
    elif args.geojson:
        print(analyser_geojson(args.geojson))
    elif args.batch:
        batch_analyse(args.batch, args.pg_conn, args.output_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
