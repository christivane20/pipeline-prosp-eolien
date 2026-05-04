{{ config(materialized='table', indexes=[{'columns': ['id_parcelle']}, {'columns': ['geometry'], 'type': 'gist'}]) }}

-- Scoring multicritère MCDM/ELECTRE TRI des parcelles cadastrales
-- Critères : vent, contraintes, foncier, réseau, accessibilité

WITH parcelles AS (
    SELECT * FROM {{ ref('stg_cadastre') }}
),

-- Distance au poste source Enedis/RTE le plus proche
dist_reseau AS (
    SELECT
        p.id_parcelle,
        MIN(ST_Distance(p.geometry, r.geometry)) AS dist_poste_m
    FROM parcelles p
    CROSS JOIN LATERAL (
        SELECT geometry FROM {{ source('raw', 'enedis_postes_source') }}
        ORDER BY p.geometry <-> geometry
        LIMIT 1
    ) r
    GROUP BY p.id_parcelle
),

-- Distance à la route principale la plus proche
dist_route AS (
    SELECT
        p.id_parcelle,
        MIN(ST_Distance(p.geometry, r.geometry)) AS dist_route_m
    FROM parcelles p
    CROSS JOIN LATERAL (
        SELECT geometry FROM {{ ref('stg_bdtopo_routes') }}
        ORDER BY p.geometry <-> geometry
        LIMIT 1
    ) r
    GROUP BY p.id_parcelle
),

-- Présence dans une ZAER arrêtée
zaer_flag AS (
    SELECT DISTINCT p.id_parcelle, TRUE AS in_zaer
    FROM parcelles p
    JOIN {{ source('raw', 'zaer_arretees') }} z
        ON ST_Intersects(p.geometry, z.geometry)
),

-- Contraintes environnementales (distance minimale aux zones sensibles)
dist_contrainte AS (
    SELECT
        p.id_parcelle,
        MIN(ST_Distance(p.geometry, c.geometry)) AS dist_min_contrainte_m
    FROM parcelles p
    CROSS JOIN {{ ref('contraintes_enviro') }} c
    GROUP BY p.id_parcelle
)

SELECT
    p.id_parcelle,
    p.code_dept,
    p.code_commune,
    p.contenance_m2,
    COALESCE(dr.dist_poste_m, 99999)        AS dist_poste_m,
    COALESCE(drt.dist_route_m, 99999)       AS dist_route_m,
    COALESCE(dc.dist_min_contrainte_m, 0)   AS dist_min_contrainte_m,
    COALESCE(zf.in_zaer, FALSE)             AS in_zaer,
    -- Score composite (0-100) — pondérations provisoires
    ROUND(
        LEAST(100,
            CASE WHEN COALESCE(zf.in_zaer, FALSE) THEN 20 ELSE 0 END
            + CASE WHEN COALESCE(dr.dist_poste_m, 99999) < 10000 THEN 25
                   WHEN COALESCE(dr.dist_poste_m, 99999) < 20000 THEN 15
                   ELSE 5 END
            + CASE WHEN COALESCE(dc.dist_min_contrainte_m, 0) > 2000 THEN 30
                   WHEN COALESCE(dc.dist_min_contrainte_m, 0) > 500 THEN 15
                   ELSE 0 END
            + CASE WHEN COALESCE(drt.dist_route_m, 99999) < 3000 THEN 25
                   WHEN COALESCE(drt.dist_route_m, 99999) < 10000 THEN 15
                   ELSE 5 END
        )
    )                                       AS score_mcdm,
    p.geometry
FROM parcelles p
LEFT JOIN dist_reseau dr    ON dr.id_parcelle = p.id_parcelle
LEFT JOIN dist_route drt    ON drt.id_parcelle = p.id_parcelle
LEFT JOIN zaer_flag zf      ON zf.id_parcelle = p.id_parcelle
LEFT JOIN dist_contrainte dc ON dc.id_parcelle = p.id_parcelle
WHERE p.contenance_m2 >= 10000  -- parcelles ≥ 1 ha
