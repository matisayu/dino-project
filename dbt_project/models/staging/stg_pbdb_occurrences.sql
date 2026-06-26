WITH source AS (
    SELECT * FROM {{ source('bronze', 'pbdb_dinosauria_raw') }}
),

staged AS (
    SELECT
        -- occurrence identity
        SAFE_CAST(REGEXP_EXTRACT(oid, r'occ:(\d+)') AS INT64)   AS occurrence_id,
        tna                                                     AS taxon_name,
        idn                                                     AS identified_name,
        -- taxonomy
        phl                                                     AS phylum_name,
        cll                                                     AS class_name,
        NULLIF(odl, 'NO_ORDER_SPECIFIED')                       AS order_name,
        NULLIF(fml, 'NO_FAMILY_SPECIFIED')                      AS family,
        gnl                                                     AS genus,
        -- modern geography
        SAFE_CAST(lat AS FLOAT64)                               AS modern_latitude,
        SAFE_CAST(lng AS FLOAT64)                               AS modern_longitude,
        cc2                                                     AS country_code,
        stp                                                     AS state,
        cny                                                     AS county,
        -- paleogeography
        SAFE_CAST(pla AS FLOAT64)                               AS paleo_latitude,
        SAFE_CAST(pln AS FLOAT64)                               AS paleo_longitude,
        -- stratigraphy
        SAFE_CAST(eag AS FLOAT64)                               AS early_age_ma,
        SAFE_CAST(lag AS FLOAT64)                               AS late_age_ma,
        oei                                                     AS early_interval,
        oli                                                     AS late_interval,
        -- discovery metadata
        att                                                     AS attribution,
        SAFE_CAST(REGEXP_EXTRACT -- check 4 digit years between 1500-2026
        (att, r'\b(1[5-9][0-9]{2}|20[0-2][0-6])\b') AS INT64)   AS discovery_year,
        TRIM(REGEXP_REPLACE(REGEXP_REPLACE -- strip parens, then trailing year
        (att, r'^\(|\)$', ''), r'\s+\d{4}[a-z]?$', ''))         AS author,
        SAFE_CAST(REGEXP_EXTRACT(cid, r'col:(\d+)') AS INT64)   AS collection_id,
        SAFE_CAST(REGEXP_EXTRACT(rid, r'ref:(\d+)') AS INT64)   AS reference_id,
        gsc                                                     AS collection_scale,
        altu                                                    AS altitude_units,
        SAFE_CAST(altv AS FLOAT64)                              AS altitude_value,
        ggc                                                     AS geology_comments
    FROM source
)

SELECT
    *,
    CASE
        WHEN late_age_ma >= 201.3 THEN 'Triassic'
        WHEN late_age_ma >= 145.0 THEN 'Jurassic'
        WHEN late_age_ma >= 66.0  THEN 'Cretaceous'
        ELSE NULL
    END                                                         AS geological_period,
    CASE
        WHEN late_age_ma >= 66.0  AND late_age_ma < 100.5 THEN 'Late Cretaceous'
        WHEN late_age_ma >= 100.5 AND late_age_ma < 145.0 THEN 'Early Cretaceous'
        WHEN late_age_ma >= 145.0 AND late_age_ma < 163.5 THEN 'Late Jurassic'
        WHEN late_age_ma >= 163.5 AND late_age_ma < 174.1 THEN 'Middle Jurassic'
        WHEN late_age_ma >= 174.1 AND late_age_ma < 201.3 THEN 'Early Jurassic'
        WHEN late_age_ma >= 201.3 AND late_age_ma < 237.0 THEN 'Late Triassic'
        WHEN late_age_ma >= 237.0 AND late_age_ma < 247.2 THEN 'Middle Triassic'
        WHEN late_age_ma >= 247.2                         THEN 'Early Triassic'
        ELSE NULL
    END                                                         AS geological_epoch,
    CASE
        WHEN modern_latitude  IS NOT NULL
        AND modern_longitude IS NOT NULL THEN 'Y'
        ELSE 'N'
    END                                                         AS has_coordinates
FROM staged
 