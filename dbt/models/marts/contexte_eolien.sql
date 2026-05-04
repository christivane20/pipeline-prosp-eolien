{{ config(materialized='table', indexes=[{'columns': ['insee_com']}, {'columns': ['geometry'], 'type': 'gist'}]) }}

WITH communes AS (
    SELECT * FROM {{ ref('stg_cadastre') }}
),
eoliennes AS (
    SELECT * FROM {{ ref('stg_eoliennes') }}
),
zaer_arr AS (
    SELECT insee_com, 'arretee' AS statut_zaer FROM {{ source('raw', 'zaer_arretees') }}
),
zaer_prop AS (
    SELECT insee_com, 'proposee' AS statut_zaer FROM {{ source('raw', 'zaer_proposees') }}
)

SELECT
    e.insee_com,
    e.nom_commune,
    e.code_dept,
    COUNT(eo.id_eolienne)                       AS nb_eoliennes,
    SUM(eo.puissance_nominale_mw)               AS puissance_totale_mw,
    COUNT(eo.id_eolienne) FILTER (
        WHERE eo.statut ILIKE '%autorisé%'
    )                                           AS nb_autorises,
    COUNT(eo.id_eolienne) FILTER (
        WHERE eo.statut ILIKE '%construit%'
    )                                           AS nb_construits,
    COALESCE(za.statut_zaer, zp.statut_zaer)    AS statut_zaer,
    e.geometry
FROM {{ source('raw', 'communes') }} e
LEFT JOIN eoliennes eo ON eo.insee_com = e.insee_com
LEFT JOIN zaer_arr za  ON za.insee_com = e.insee_com
LEFT JOIN zaer_prop zp ON zp.insee_com = e.insee_com
GROUP BY e.insee_com, e.nom_commune, e.code_dept, za.statut_zaer, zp.statut_zaer, e.geometry
