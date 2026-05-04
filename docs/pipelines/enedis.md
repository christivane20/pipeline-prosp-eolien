# Notice technique — Pipeline Enedis / Agence ORE / RTE

## Sources

### Agence ORE

- **Nom** : Données ouvertes du réseau de distribution électrique
- **Producteur** : Agence ORE (Opérateurs de Réseaux d'Énergie)
- **URL** : opendata.agenceore.fr
- **Licence** : Open Data Commons
- **Score MCDM** : 77/100 — Classe A

### RTE Réseau

- **Nom** : Capacités d'accueil des postes sources
- **Producteur** : RTE (Réseau de Transport d'Électricité)
- **URL** : opendata.reseaux-energies.fr
- **Score MCDM** : 77/100 — Classe A (mutualisé avec ORE)

## Utilisation éolienne

Le raccordement électrique est un **critère de faisabilité décisif** :

- **Postes source HTA/HTB** : point de raccordement des parcs éoliens
- **Capacités d'accueil** : MW disponibles sans renforcement réseau
- **Bilan électrique communes** : contexte consommation/production local

## Données ingérées

| Source | Table PostGIS | Description |
|--------|---------------|-------------|
| ORE postes source | `raw.enedis_postes_source` | Postes HTA/HTB géolocalisés |
| ORE raccordements | `raw.enedis_raccordements` | Capacités MW disponibles |
| ORE bilan élec | `raw.enedis_bilan_elec` | Bilan commune (CSV) |
| RTE raccordements | `raw.rte_raccordements` | Capacités HTB (>100MW) |

## DAG Airflow

- **DAG ID** : `dag_enedis_ore`
- **Fichier** : `dags/dag_enedis.py`
- **Planification** : `0 4 1 * *` (mensuel)

## Points d'attention

- Les capacités d'accueil sont indicatives — vérifier avec le gestionnaire de réseau
- Le format CSV bilan élec utilise le séparateur `;`
- Les postes source Enedis ne couvrent que la BT/MT — les HTA/HTB sont chez RTE
- Les données de capacité sont actualisées après chaque Schema Régional de Raccordement
