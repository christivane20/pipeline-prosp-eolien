# Architecture du pipeline SIG éolien

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SOURCES OPEN DATA (46)                        │
│  Cadastre · BD TOPO · Enedis · SIA · RNE · ZAER · INPN · MCC...   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ HTTP / WFS / API REST
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION — Apache Airflow                   │
│  dag_cadastre · dag_bdtopo · dag_enedis · dag_obstacles_sia         │
│  dag_elus_rne · dag_zaer · dag_monuments_histo                      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ ogr2ogr / GeoPandas
                           ▼
┌──────────────────────────────────────────┐
│         STOCKAGE — PostgreSQL/PostGIS     │
│  Schema raw   : données brutes            │
│  Schema staging : vues normalisées (dbt)  │
│  Schema mart  : tables métier (dbt)       │
│  Schema log   : audit pipeline            │
└──────────┬───────────────────────────────┘
           │                │
           │ dbt            │ FastAPI
           ▼                ▼
┌──────────────────┐  ┌─────────────────────────────────┐
│ TRANSFORMATION   │  │        API REST géospatiale       │
│ dbt models       │  │  /communes · /zaer · /eoliennes  │
│ staging + marts  │  │  /contraintes · /analyse-ia      │
└──────────────────┘  └─────────────────────────────────┘
           │
           │                     ┌─────────────────────────┐
           ├────────────────────►│   VISUALISATION          │
           │                     │  QGIS Server · Lizmap    │
           │                     │  GeoServer · pg_tileserv │
           │                     └─────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│                     CLOUD AWS                             │
│  S3 : rasters COG (vent 140m, ortho, MNT)               │
│  RDS : PostGIS managé (prod)                             │
│  Lambda : déclenchement pipeline serverless              │
└──────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│                  IA GÉOSPATIALE                           │
│  Claude API : analyse automatique couches (claude_analysis.py) │
│  YOLOv11    : détection éoliennes sur satellite (yolo_detection.py) │
│  MLflow     : tracking expériences ML                    │
└──────────────────────────────────────────────────────────┘
```

---

## Stack technique détaillée

### Base de données

- **PostgreSQL 15 + PostGIS 3.4** en Docker (dev) et AWS RDS (prod)
- Schémas : `raw` (ingest brut) → `staging` (nettoyage dbt) → `mart` (tables métier)
- Extensions : `postgis`, `postgis_raster`, `pg_tileserv`

### Orchestration

- **Apache Airflow 2.x** — 7 DAGs couvrant les 46 sources
- Planifications : mensuelle (Cadastre, Enedis, RNE), trimestrielle (BD TOPO, SIA), hebdomadaire (ZAER)
- Retry automatique, alertes email en cas d'échec

### Transformation

- **dbt** (data build tool) — modèles versionnés SQL
- Staging : vues normalisées (EPSG:2154, colonnes standardisées)
- Marts : `contexte_eolien`, `contraintes_enviro`, `scoring_parcelles`

### API

- **FastAPI + Uvicorn** sur port 8000
- Endpoints GeoJSON natifs (GeoPandas `__geo_interface__`)
- Endpoint POST `/analyse-ia` : appel Claude API synchrone

### Visualisation

- **Lizmap** (QGIS Server) — projets QGIS publiés en ligne
- **GeoServer** — WMS/WFS pour interopérabilité
- **pg_tileserv** — tuiles vectorielles MVT depuis PostGIS

### Cloud AWS

- **S3** : stockage rasters COG (Cloud Optimized GeoTIFF)
- **RDS** : PostGIS managé multi-AZ (prod)
- **Lambda** : déclenchement DAGs Airflow via API Airflow REST

### IA géospatiale

- **Claude API** (`claude-sonnet-4-6`) — analyse contexte éolien, verdict faisabilité
- **YOLOv11** (Ultralytics) — détection éoliennes sur images Sentinel-2/Pléiades
- **MLflow** — tracking métriques (precision, recall, F1 détection)

---

## Flux de données type — Cadastre DGFiP

```
1. Airflow (dag_cadastre) déclenché le 1er du mois à 2h
   ↓
2. Téléchargement GeoJSON cadastre.data.gouv.fr (95 départements)
   ↓
3. Reprojection EPSG:4326 → EPSG:2154 (Lambert 93)
   ↓
4. Chargement dans raw.cadastre_parcelles (GeoPandas → PostGIS)
   ↓
5. dbt run --select staging.stg_cadastre → vue normalisée
   ↓
6. dbt run --select marts.scoring_parcelles → scoring MCDM
   ↓
7. Visualisation Lizmap / API FastAPI /zaer
```

---

## Sécurité et gouvernance

- Secrets AWS via **AWS Secrets Manager** (jamais en clair dans le code)
- Variables d'environnement pour connexions locales
- `.gitignore` exclut `data/raw/`, `*.tif`, `*.zip`, credentials
- Logs Airflow tracent toutes les exécutions et erreurs

---

## Déploiement

### Local (développement)

```bash
docker-compose up -d         # PostGIS + pgAdmin
python scripts/01_download_data.py --source cadastre --dept 60
python scripts/02_load_postgis.py --source cadastre --dept 60
cd dbt && dbt run
uvicorn scripts.04_api_fastapi:app --reload
```

### Production AWS

```bash
# Infrastructure
terraform apply              # RDS + Lambda + S3 (non inclus dans ce repo)

# Pipeline
aws lambda invoke --function-name eolien-pipeline-trigger \
    --payload '{"source":"all"}' response.json
```
