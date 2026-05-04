# 🌬️ Pipeline SIG — Prospection Éolienne Onshore

> Pipeline géospatial open source pour la gestion des données géospatiales
> en prospection éolienne onshore. Développé par **Christ Ivane KOUADIO** — ESGT (2026).

---

## 🎯 Objectif

Construire un pipeline **bout-en-bout, automatisé et cloud-ready** pour la gestion des données géospatiales en prospection éolienne :

- Ingestion automatique de **46 sources open data** géographiques
- Stockage et traitement dans **PostgreSQL/PostGIS**
- Orchestration des mises à jour avec **Apache Airflow**
- Publication cartographique via **GeoServer + Lizmap**
- API géospatiale REST avec **FastAPI**
- Déploiement cloud sur **AWS** (S3, RDS, Lambda)
- Intégration **IA (Claude API)** pour l'analyse automatique des couches

---

## 🧱 Stack technique

| Couche | Technologie |
|--------|------------|
| **Base de données** | PostgreSQL 15 · PostGIS 3.4 |
| **Traitement géospatial** | Python · GeoPandas · GDAL/OGR · Shapely · SQLAlchemy |
| **Orchestration pipelines** | Apache Airflow · pgAgent |
| **Transformation données** | dbt (data build tool) |
| **Visualisation web** | QGIS Server · Lizmap · GeoServer · pg_tileserv |
| **API REST** | FastAPI · Uvicorn |
| **Cloud** | AWS S3 · AWS RDS PostGIS · AWS Lambda |
| **Conteneurisation** | Docker · docker-compose |
| **IA géospatiale** | Claude API (Anthropic) · YOLOv11 |
| **Formats cloud-native** | COG (Cloud Optimized GeoTIFF) · STAC |

---

## 📡 Sources de données — 46 sources documentées

| Thème | Sources |
|-------|---------|
| **Foncier** | Cadastre DGFiP (×95 dép.) · MAJIC personnes morales · RPG PAC |
| **Infrastructure** | RTE réseau électrique · Enedis/ORE · IGN BD TOPO · Géorisques ICPE · PPRNi |
| **Environnement** | INPN ZNIEFF · Natura 2000 · Zones humides · BRGM géologie · Haies IGN |
| **Aviation** | SIA/DGAC obstacles · Faisceaux hertziens ANFR · Contraintes aéro |
| **Contexte éolien** | Éoliennes DREALs (×12 régions) · ZAER · ZAER arrêtées |
| **Vent** | Cerema/Météo France 140m · ADEME 100m · UL spd100/140m |
| **Paysage** | Monuments historiques · Sites classés/inscrits · Atlas patrimoines |
| **Administratif** | RNE Élus (API) · Admin Express IGN · Communes/Départements/Régions |

> 📊 Grille complète de scoring et gouvernance : `data/suivi_sources_sig.xlsx`
> Modèle multicritères (MCDM/ELECTRE TRI) documenté dans `docs/scoring_model.md`

---

## 🏗️ Architecture du projet

```
pipeline-prosp-eolien/
│
├── docker-compose.yml
│
├── dags/
│   ├── dag_cadastre.py
│   ├── dag_bdtopo.py
│   ├── dag_enedis.py
│   ├── dag_obstacles_sia.py
│   ├── dag_elus_rne.py
│   ├── dag_zaer.py
│   └── dag_monuments_histo.py
│
├── scripts/
│   ├── 01_download_data.py
│   ├── 02_load_postgis.py
│   ├── 03_transform_dbt.py
│   ├── 04_api_fastapi.py
│   └── 05_qgis_claude_plugin.py
│
├── dbt/
│   └── models/
│       ├── staging/
│       └── marts/
│
├── aws/
│   ├── s3_raster_store.py
│   ├── rds_postgis_connect.py
│   └── lambda_pipeline.py
│
├── ml/
│   ├── yolo_detection.py
│   └── claude_analysis.py
│
├── data/
│   ├── suivi_sources_sig.xlsx
│   └── sample/
│
└── docs/
    ├── scoring_model.md
    ├── architecture.md
    └── pipelines/
```

---

## 🚀 Démarrage rapide

```bash
# Cloner le repo
git clone https://github.com/christivane20/pipeline-prosp-eolien.git
cd pipeline-prosp-eolien

# Lancer la stack complète
docker-compose up -d

# Vérifier que PostGIS est up
docker exec -it postgis psql -U lizmap -c "SELECT PostGIS_Version();"

# Charger un département test (Oise - 60)
python scripts/01_download_data.py --source cadastre --dept 60
python scripts/02_load_postgis.py --source cadastre --dept 60
```

---

## 🤖 Intégration IA — Claude API dans QGIS

```python
import anthropic
import geopandas as gpd

def analyser_contexte_eolien(gpkg_path: str) -> str:
    gdf = gpd.read_file(gpkg_path)
    stats = {
        "nb_projets": len(gdf),
        "statuts": gdf["statut"].value_counts().to_dict(),
        "puissance_totale_mw": gdf["puissance_parc_max_mw"].sum()
    }
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"Analyse ce contexte éolien régional : {stats}"
        }]
    )
    return response.content[0].text
```

---

## 📊 Modèle de scoring multicritères

- **8 critères** pondérés (accessibilité, criticité métier, stabilité format...)
- **Coefficients validés** par sondage Delphi auprès d'experts SIG
- **Seuils** : Jenks (1967), partition équidistante, fuzzy sets (Zadeh, 1965)
- **Classification** : A (automatiser) · B (planifier) · C (semi-auto) · D (manuel)

> 📄 Documentation complète : `docs/scoring_model.md`

---

## 📈 Résultats

| Métrique | Avant | Après | Gain |
|----------|-------|-------|------|
| MAJ Cadastre ×95 dép. | ~40h | ~2h | **−95 %** |
| MAJ Obstacles SIA | ~3h | ~15 min | **−92 %** |
| MAJ Élus RNE | ~2h | automatique | **−100 %** |
| MAJ BD TOPO ×6 tables | ~20h | ~3h | **−85 %** |
| Inventaire sources | non documenté | 46 sources scorées | ✅ |

---

## 🗺️ Roadmap

- [x] Architecture BDD PostGIS documentée
- [x] 46 sources inventoriées et scorées (Excel + modèle MCDM)
- [x] Application Flask gouvernance SIG
- [x] Docker PostGIS local opérationnel
- [x] DAGs Airflow (Cadastre, BD TOPO, Enedis, Obstacles, Élus, ZAER, Monuments)
- [x] dbt models (staging + marts)
- [x] API FastAPI géospatiale
- [ ] Déploiement AWS (S3 + RDS) — en cours
- [ ] Plugin QGIS + Claude API — en cours
- [ ] Détection éoliennes YOLOv11 — en cours
- [ ] STAC catalog + COG rasters
- [ ] Dashboard Streamlit / Grafana

---

## 👤 Auteur

**Christ Ivane KOUADIO**
Ingénieur Géomètre-Topographe · Géomatique & Data Géospatiale — ESGT (2026)
Spécialisation : Geospatial Data Engineering · Énergie · IA géospatiale

[![Kaggle](https://img.shields.io/badge/Kaggle-Geospatial_Analysis-blue)](https://www.kaggle.com/learn/certification/christivanekouadio/geospatial-analysis)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-christ--ivane--kouadio-blue)](https://linkedin.com/in/christ-ivane-kouadio)

---

## 📄 Licence

MIT — libre d'utilisation, d'adaptation et de redistribution avec attribution.
