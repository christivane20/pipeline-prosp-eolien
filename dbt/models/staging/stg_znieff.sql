{{ config(materialized='view') }}

SELECT
    id_mnhn                 AS id_znieff,
    nom_cite                AS nom,
    "TYPEZON"               AS type_zone,   -- 1 = ZNIEFF I, 2 = ZNIEFF II
    "LB_REG"                AS region,
    "LB_DEP"                AS departement,
    ST_Area(geometry) / 1e4 AS surface_ha,
    geometry
FROM {{ source('raw', 'znieff') }}
WHERE geometry IS NOT NULL
  AND ST_IsValid(geometry)
