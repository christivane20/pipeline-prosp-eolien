# Notice technique — Pipeline Cadastre DGFiP

## Source

- **Nom** : Cadastre — Plan cadastral informatisé (PCI Vecteur)
- **Producteur** : DGFiP (Direction générale des Finances publiques)
- **Distributeur** : cadastre.data.gouv.fr (Etalab)
- **Licence** : Licence Ouverte 2.0 (Etalab)
- **Score MCDM** : 92/100 — Classe A (automatiser)

## Format

- GeoJSON par département
- CRS source : EPSG:4326 (WGS84)
- CRS cible : EPSG:2154 (Lambert 93)
- Entités : parcelles cadastrales polygones

## URL de téléchargement

```
https://cadastre.data.gouv.fr/bundler/cadastre-etalab/departements/{dept}/geojson/parcelles
```

Avec `{dept}` = code département sur 2 caractères (`01`→`95`, `2A`, `2B`).

## Schéma source

| Champ | Type | Description |
|-------|------|-------------|
| id | STRING | Identifiant unique parcelle |
| commune | STRING | Code INSEE commune (5 chiffres) |
| prefixe | STRING | Préfixe section |
| section | STRING | Section cadastrale |
| numero | STRING | Numéro de parcelle |
| contenance | INTEGER | Contenance en m² |
| geometry | MULTIPOLYGON | Géométrie parcelle |

## DAG Airflow

- **DAG ID** : `dag_cadastre_dgfip`
- **Fichier** : `dags/dag_cadastre.py`
- **Planification** : `0 2 1 * *` (1er du mois à 2h)
- **Durée estimée** : ~90 min (95 départements, 5 en parallèle)
- **Table cible** : `raw.cadastre_parcelles`

## Modèle dbt

- **Staging** : `dbt/models/staging/stg_cadastre.sql`
- **Mart** : `dbt/models/marts/scoring_parcelles.sql` (utilise le cadastre)

## Utilisation métier

- Identification des propriétaires fonciers (croisement MAJIC)
- Calcul de surfaces de parcelles
- Scoring MCDM parcelles candidates
- Cartographie foncière des projets

## Points d'attention

- Certains départements (75, 92-95) ont un volume très élevé (>500 MB)
- Les DOM-TOM ne sont pas couverts par cette source
- Le cadastre de Mayotte est disponible sur une URL différente
- Mettre à jour le `timeout` à 600s pour les grands départements
