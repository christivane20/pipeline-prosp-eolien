"""Plugin QGIS — Analyse automatique de couches éoliennes via Claude API.

Intégration standalone (utilisable hors QGIS) ou en tant que script QGIS Processing.
Usage standalone:
    python scripts/05_qgis_claude_plugin.py --layer data/sample/eoliennes.gpkg
"""
import argparse
import json
import os
import anthropic
import geopandas as gpd
import pandas as pd


MODEL = "claude-sonnet-4-6"


def analyser_contexte_eolien(gpkg_path: str, rayon_km: float = 30.0) -> str:
    gdf = gpd.read_file(gpkg_path)
    stats: dict = {
        "nb_projets": len(gdf),
        "crs": str(gdf.crs),
        "colonnes": list(gdf.columns.drop("geometry", errors="ignore")),
    }
    if "statut" in gdf.columns:
        stats["statuts"] = gdf["statut"].value_counts().to_dict()
    if "puissance_parc_max_mw" in gdf.columns:
        stats["puissance_totale_mw"] = round(float(gdf["puissance_parc_max_mw"].sum()), 1)
        stats["puissance_moyenne_mw"] = round(float(gdf["puissance_parc_max_mw"].mean()), 1)
    if "nb_eoliennes" in gdf.columns:
        stats["nb_machines_total"] = int(gdf["nb_eoliennes"].sum())
    if gdf.crs and gdf.crs.is_geographic:
        gdf = gdf.to_crs(epsg=2154)
    bbox = gdf.total_bounds
    stats["emprise_km2"] = round((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) / 1e6, 1)

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1200,
        system=(
            "Tu es un expert en prospection éolienne onshore en France. "
            "Tu analyses des données SIG géospatiales et identifies les tendances, "
            "opportunités et risques pour le développement éolien."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Analyse ce contexte éolien régional (rayon {rayon_km} km) "
                f"et identifie les tendances :\n{json.dumps(stats, ensure_ascii=False, indent=2)}"
            ),
        }],
    )
    return response.content[0].text


def analyser_contraintes(contraintes_geojson: str, commune_insee: str) -> str:
    gdf = gpd.read_file(contraintes_geojson)
    summary: dict = {
        "commune_insee": commune_insee,
        "nb_contraintes": len(gdf),
        "types": gdf["type_contrainte"].value_counts().to_dict() if "type_contrainte" in gdf.columns else {},
    }
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": (
                f"Pour la commune {commune_insee}, évalue la faisabilité éolienne "
                f"au regard de ces contraintes réglementaires :\n"
                f"{json.dumps(summary, ensure_ascii=False, indent=2)}\n"
                "Donne un verdict (favorable / mitigé / défavorable) avec justification."
            ),
        }],
    )
    return response.content[0].text


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyse IA de couches éoliennes via Claude API")
    parser.add_argument("--layer", required=True, help="Chemin vers le fichier GeoPackage/GeoJSON")
    parser.add_argument("--rayon-km", type=float, default=30.0)
    parser.add_argument("--contraintes", help="Fichier GeoJSON contraintes (optionnel)")
    parser.add_argument("--insee", help="Code INSEE commune (si --contraintes fourni)")
    args = parser.parse_args()

    print("=== Analyse contexte éolien ===")
    analyse = analyser_contexte_eolien(args.layer, rayon_km=args.rayon_km)
    print(analyse)

    if args.contraintes and args.insee:
        print("\n=== Analyse contraintes réglementaires ===")
        verdict = analyser_contraintes(args.contraintes, args.insee)
        print(verdict)


if __name__ == "__main__":
    main()
