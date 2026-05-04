# Notice technique — Pipeline Élus RNE

## Source

- **Nom** : Répertoire National des Élus (RNE)
- **Producteur** : DILA (Direction de l'information légale et administrative)
- **Distributeur** : data.gouv.fr
- **Licence** : Licence Ouverte 2.0
- **Score MCDM** : 85/100 — Classe A

## Utilisation éolienne

En prospection foncière éolienne, identifier les **maires et adjoints** des communes d'implantation est critique pour :

- Initier le dialogue avec la commune avant dépôt de permis
- Vérifier les mandats en cours et les changements électoraux
- Anticiper les positions politiques locales sur l'éolien

## Fichiers CSV disponibles

| Dataset | URL data.gouv.fr | Contenu |
|---------|-----------------|---------|
| Conseillers municipaux | /r/d5f400de... | Maires, adjoints, conseillers |
| Conseillers départementaux | /r/601ef073... | Élus CG/CD |
| Conseillers régionaux | /r/430e13f9... | Élus CR |

## DAG Airflow

- **DAG ID** : `dag_elus_rne`
- **Fichier** : `dags/dag_elus_rne.py`
- **Planification** : `0 6 1 * *` (mensuel — après les élections partielles)
- **Tables cibles** : `raw.rne_conseillers_municipaux`, `raw.contacts_projet_elus`

## Logique de croisement

Le DAG croise automatiquement les élus avec la table `raw.communes_projet` (communes dans le périmètre des projets en développement) pour générer `raw.contacts_projet_elus`.

## Points d'attention

- Le CSV utilise le séparateur `;` et l'encodage UTF-8
- Les noms de colonnes contiennent des accents → nettoyage dans le DAG
- Les données sont mises à jour après chaque élection (municipales, partielles)
- Certaines communes peuvent avoir plusieurs maires (intérim, fusion)
