{{ config(materialized='view') }}

WITH src AS (
    SELECT * FROM {{ source('raw', 'eoliennes_georisques') }}
    UNION ALL
    SELECT * FROM {{ source('raw', 'eoliennes_dreals') }}
)

SELECT
    identifiant_s3ic                        AS id_eolienne,
    nom_etablissement                       AS nom_parc,
    adresse_etablissement                   AS adresse,
    code_commune                            AS insee_com,
    nom_commune,
    code_departement                        AS code_dept,
    etat_de_l_installation_actuel           AS statut,
    date_d_autorisation                     AS date_autorisation,
    regime                                  AS regime_icpe,
    CAST(puissance_nominale_mw AS NUMERIC)  AS puissance_nominale_mw,
    geometry
FROM src
WHERE geometry IS NOT NULL
  AND code_activite_naf LIKE '35%'  -- production électricité
