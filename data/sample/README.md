# Données exemples — Département Oise (60)

Ce répertoire contient des données exemple pour tester le pipeline sur le département de l'Oise (code 60).

## Contenu attendu (non versionné — généré par les scripts)

| Fichier | Source | Script générateur |
|---------|--------|------------------|
| `cadastre_60.geojson` | Cadastre DGFiP | `scripts/01_download_data.py --source cadastre --dept 60` |
| `zaer_60.geojson` | data.gouv.fr | `scripts/01_download_data.py --source zaer` |
| `eoliennes_60.gpkg` | Géorisques | Extraction manuelle |

## Génération

```bash
python scripts/01_download_data.py --source cadastre --dept 60
python scripts/02_load_postgis.py --source cadastre --dept 60
```

Les fichiers volumineux (> 100 MB) sont exclus du repo via `.gitignore`.
