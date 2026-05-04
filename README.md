# 🌬️ Pipeline SIG — Prospection Éolienne Onshore

> Pipeline géospatial open source reproduisant et améliorant l'architecture SIG
> Développé dans le cadre du TFE Ingénieur ESGT (wpd, 2026) par **Christ Ivane KOUADIO**.

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
