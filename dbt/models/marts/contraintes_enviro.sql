{{ config(materialized='table', indexes=[{'columns': ['geometry'], 'type': 'gist'}]) }}

SELECT
    'ZNIEFF I'      AS type_contrainte,
    500             AS rayon_eloignement_m,
    nom             AS libelle,
    geometry
FROM {{ ref('stg_znieff') }}
WHERE type_zone = '1'

UNION ALL

SELECT
    'ZNIEFF II',
    0,
    nom,
    geometry
FROM {{ ref('stg_znieff') }}
WHERE type_zone = '2'

UNION ALL

SELECT
    'MH classé',
    500,
    libelle         AS libelle,
    geometry
FROM {{ source('raw', 'mcc_monuments_historiques_classes') }}

UNION ALL

SELECT
    'MH inscrit',
    500,
    libelle,
    geometry
FROM {{ source('raw', 'mcc_monuments_historiques_inscrits') }}

UNION ALL

SELECT
    'Site Natura 2000',
    0,
    sitename        AS libelle,
    geometry
FROM {{ source('raw', 'natura2000') }}
