{{ config(materialized='view') }}

SELECT
    id                          AS id_parcelle,
    dept                        AS code_dept,
    "commune"                   AS code_commune,
    "prefixe"                   AS prefixe,
    "section"                   AS section,
    "numero"                    AS numero,
    COALESCE("contenance", 0)   AS contenance_m2,
    geometry
FROM {{ source('raw', 'cadastre_parcelles') }}
WHERE geometry IS NOT NULL
  AND ST_IsValid(geometry)
