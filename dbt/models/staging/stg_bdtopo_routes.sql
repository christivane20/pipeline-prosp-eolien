{{ config(materialized='view') }}

SELECT
    gid,
    "NATURE"        AS nature,
    "NOM_1_G"       AS nom_voie,
    "IMPORTANCE"    AS importance,
    "LARGEUR"       AS largeur_m,
    "NB_VOIES"      AS nb_voies,
    geometry
FROM {{ source('raw', 'bdtopo_routes') }}
WHERE geometry IS NOT NULL
  AND "NATURE" IN ('Route nationale', 'Route départementale', 'Route à 2 chaussées')
