{{ config(materialized='view') }}

SELECT
    gid,
    "CODETYPE"      AS code_type,
    "LIBELTYPE"     AS libelle_type,
    "HAUTEUR"       AS hauteur_m,
    "HAUTEUR_SOL"   AS hauteur_sol_m,
    "BALISE"        AS balise,
    "IDENTIFIANT"   AS identifiant_sia,
    geometry
FROM {{ source('raw', 'sia_obstacles') }}
WHERE geometry IS NOT NULL
  AND "HAUTEUR" >= 50
