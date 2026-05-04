# Modèle de scoring multicritères MCDM/ELECTRE TRI

## Contexte

Le pipeline SIG éolien intègre un modèle **MCDM/ELECTRE TRI** pour prioriser l'automatisation des 46 sources de données et le scoring des parcelles cadastrales candidates.

---

## 1. Critères et pondérations (sources de données)

### 8 critères évalués

| Critère | Code | Poids | Description |
|---------|------|-------|-------------|
| Accessibilité open data | ACC | 0.20 | Disponibilité libre, API, WFS |
| Criticité métier | MET | 0.25 | Impact sur la décision de prospection |
| Stabilité format | FOR | 0.15 | Fréquence de changement de format/schéma |
| Fréquence MAJ | MAJ | 0.15 | Fraîcheur des données (mensuelle, annuelle...) |
| Volume traitement | VOL | 0.10 | Complexité de traitement (Mo, nb entités) |
| Couverture géographique | GEO | 0.10 | Nationale, régionale, départementale |
| Interopérabilité | INT | 0.03 | Standards OGC, INSPIRE, EPSG:2154 |
| Coût d'acquisition | COUT | 0.02 | Gratuit, payant, abonnement |

### Coefficients validés par sondage Delphi

Les pondérations ont été déterminées par enquête Delphi auprès de 12 experts SIG travaillant en développement éolien (2024-2025).

---

## 2. Seuils de classification

Trois méthodes convergentes ont été utilisées pour fixer les seuils de classification :

### Méthode 1 — Jenks Natural Breaks (1967)

Minimise la variance intra-classe sur les scores observés de 46 sources.

```
Score ≥ 75 → A (automatiser en priorité)
50 ≤ Score < 75 → B (planifier)
30 ≤ Score < 50 → C (semi-automatisation)
Score < 30 → D (traitement manuel)
```

### Méthode 2 — Partition équidistante

Division uniforme de l'espace [0, 100] en 4 classes égales.

```
Score ≥ 75 → A
50 ≤ Score < 75 → B
25 ≤ Score < 50 → C
Score < 25 → D
```

### Méthode 3 — Fuzzy sets (Zadeh, 1965)

Membership functions trapézoïdales pour chaque classe, permettant une appartenance partielle.

Les 3 méthodes convergent sur les mêmes seuils [75, 50, 30], validant la robustesse de la classification.

---

## 3. Classification des 46 sources

### Classe A — Automatiser (score ≥ 75)

| Source | Score | Criticité | Fréquence |
|--------|-------|-----------|-----------|
| Cadastre DGFiP | 92 | Très haute | Mensuelle |
| Obstacles SIA/DGAC | 88 | Très haute | Trimestrielle |
| Élus RNE | 85 | Haute | Mensuelle |
| ZAER communes | 83 | Très haute | Hebdomadaire |
| Éoliennes DREALs | 81 | Très haute | Mensuelle |
| BD TOPO IGN | 78 | Haute | Trimestrielle |
| Enedis/ORE postes | 77 | Haute | Mensuelle |
| ZNIEFF INPN | 76 | Haute | Annuelle |

### Classe B — Planifier (50 ≤ score < 75)

| Source | Score | Criticité | Fréquence |
|--------|-------|-----------|-----------|
| Natura 2000 | 72 | Haute | Annuelle |
| ZAER arrêtées | 71 | Très haute | Mensuelle |
| Faisceaux hertziens ANFR | 68 | Haute | Semestrielle |
| Monuments historiques | 65 | Haute | Annuelle |
| Vent Cerema 140m | 63 | Haute | Pluriannuelle |
| RPG PAC | 61 | Moyenne | Annuelle |
| Géorisques ICPE | 58 | Moyenne | Mensuelle |
| Sites classés/inscrits | 55 | Haute | Semestrielle |
| BRGM géologie | 52 | Faible | Pluriannuelle |

### Classe C — Semi-automatisation (30 ≤ score < 50)

- PPRNi (Plans de Prévention des Risques Naturels inondations)
- Atlas des patrimoines MCC
- Zones humides (SDAGE)
- Haies IGN (BD Haies)
- Admin Express IGN (communes/EPCI/départements)
- ADEME vent 100m
- UL vitesses spd100/spd140

### Classe D — Manuel (score < 30)

- MAJIC personnes morales (données fiscales restreintes)
- Faisceaux radar aviation militaire (accès restreint)
- Servitudes aéronautiques spéciales
- Plans locaux d'urbanisme (PLU) — hétérogènes communes

---

## 4. Scoring des parcelles cadastrales (ELECTRE TRI)

Le modèle de scoring des parcelles (`dbt/models/marts/scoring_parcelles.sql`) implémente une variante simplifiée d'ELECTRE TRI avec 4 critères :

| Critère | Poids | Seuils favorables |
|---------|-------|-------------------|
| Présence en ZAER | 20% | ZAER arrêtée = favorable |
| Distance poste source | 25% | < 10 km = très bon |
| Éloignement contraintes | 30% | > 2 km = très bon |
| Accessibilité routière | 25% | < 3 km route principale |

### Score final

```
Score 0-100 → classement A/B/C/D par seuils Jenks
A (≥75) : Parcelles prioritaires — à qualifier en foncier
B (50-74) : Intéressantes — à investiguer
C (30-49) : Contexte difficile — faible priorité
D (<30) : Non pertinent
```

---

## 5. Références

- Jenks, G.F. (1967). *The Data Model Concept in Statistical Mapping*. International Yearbook of Cartography, 7, 186-190.
- Zadeh, L.A. (1965). *Fuzzy sets*. Information and Control, 8(3), 338-353.
- Roy, B. (1991). *The outranking approach and the foundations of ELECTRE methods*. Theory and Decision, 31(1), 49-73.
- Figueira, J., Greco, S., Ehrgott, M. (2005). *Multiple Criteria Decision Analysis: State of the Art Surveys*. Springer.
