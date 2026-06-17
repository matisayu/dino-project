WITH scored AS (
    SELECT * FROM {{ ref('int_occurrences_scored') }}
)

SELECT
    -- identity
    occurrence_id,
    taxon_name,
    identified_name,
    genus,
    family,
    order_name,
    class_name,

    -- modern geography
    modern_latitude,
    modern_longitude,
    country_code,
    state,

    -- paleogeography
    paleo_latitude,
    paleo_longitude,

    -- time
    geological_period,
    geological_epoch,
    early_age_ma,
    late_age_ma,
    early_interval,
    late_interval,

    -- discovery
    discovery_year,
    attribution,
    collection_id,

    -- quality
    quality_score

FROM scored
WHERE modern_latitude  IS NOT NULL
  AND modern_longitude IS NOT NULL
  AND geological_period IS NOT NULL
  AND discovery_year    IS NOT NULL