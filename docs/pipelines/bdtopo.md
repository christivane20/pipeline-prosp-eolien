# Notice technique — Pipeline BD TOPO IGN

## Source

- **Nom** : BD TOPO® — Base de données topographique nationale
- **Producteur** : IGN (Institut national de l'information géographique et forestière)
- **Distributeur** : Géoportail API (data.geopf.fr)
- **Licence** : Licence Ouverte 2.0
- **Score MCDM** : 78/100 — Classe A (automatiser)

## Couches ingérées

| Couche WFS | Table PostGIS | Utilisation éolien |
|------------|---------------|-------------------|
| ROUTE_PRIMAIRE | `raw.bdtopo_routes` | Accessibilité site, convois |
| HAIE | `raw.bdtopo_haies` | Contrainte haies (loi EAV) |
| ZONE_DE_VEGETATION | `raw.bdtopo_vegetation` | Contexte paysager |
| BATIMENT | `raw.bdtopo_batiments` | Riverains, distances |
| LIGNE_ELECTRIQUE | `raw.bdtopo_lignes_elec` | Contraintes aériennes |
| PYLONE | `raw.bdtopo_pylones` | Obstacles aviation |

## Endpoint WFS

```
https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature
&TYPENAMES=BDTOPO_V3:{LAYER}&SRSNAME=EPSG:2154
```

## DAG Airflow

- **DAG ID** : `dag_bdtopo_ign`
- **Fichier** : `dags/dag_bdtopo.py`
- **Planification** : `0 3 1 */3 *` (trimestriel)
- **Outil** : `ogr2ogr` (pour les grands volumes WFS)
- **Timeout** : 30 min par couche

## Points d'attention

- La couche BATIMENT est très volumineuse (~10 GB national)
- Préférer un filtre spatial (BBOX) pour les tests sur une zone
- Les haies sont issues de la BD Haies IGN (fusion BDTOPO + RPG + OSO)
- La version BDTOPO V3 utilise le préfixe `BDTOPO_V3:` dans les type names WFS
