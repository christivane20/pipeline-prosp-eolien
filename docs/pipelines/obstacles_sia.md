# Notice technique — Pipeline Obstacles SIA/DGAC + ANFR

## Sources

### Obstacles aéronautiques SIA

- **Nom** : Base de données des obstacles à la navigation aérienne (BDOSA)
- **Producteur** : SIA (Service de l'Information Aéronautique) — DGAC
- **Licence** : Ouverte (usage non commercial)
- **Score MCDM** : 88/100 — Classe A

### Faisceaux hertziens ANFR

- **Nom** : Observatoire ANFR — Faisceaux hertziens
- **Producteur** : ANFR (Agence Nationale des Fréquences)
- **Licence** : Open Data
- **Score MCDM** : 68/100 — Classe B

## Utilisation éolienne

Les obstacles SIA et faisceaux hertziens définissent des **servitudes aéronautiques** et des **couloirs de propagation** incompatibles avec l'implantation d'éoliennes :

- **Obstacles > 50m** : balisage obligatoire, contraintes de gabarit pour les éoliennes voisines
- **Zones D/R/P** : zones réglementées, restreintes, prohibées (incompatibles)
- **Faisceaux hertziens** : couloir de 300m de part et d'autre = servitude de dégagement

## DAG Airflow

- **DAG ID** : `dag_obstacles_sia_anfr`
- **Fichier** : `dags/dag_obstacles_sia.py`
- **Planification** : `0 1 1 */3 *` (trimestriel)
- **Tables cibles** : `raw.sia_obstacles`, `raw.anfr_faisceaux_hertziens`

## Points d'attention

- La BDOSA est publiée en format SHP zippé trimestriellement
- Filtrer les obstacles < 50m pour alléger le volume (inutiles en éolien)
- Les coordonnées source sont en EPSG:4326 (WGS84)
- Les faisceaux ANFR ont une géométrie lineaire (axe du faisceau) → buffer de 300m
