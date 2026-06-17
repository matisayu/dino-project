WITH occurrences AS (
    SELECT * FROM {{ ref('stg_pbdb_occurrences') }}
)

SELECT
    *,
    (
        CASE WHEN modern_latitude  IS NOT NULL
              AND modern_longitude IS NOT NULL THEN 1 ELSE 0 END
      + CASE WHEN discovery_year   IS NOT NULL THEN 1 ELSE 0 END
      + CASE WHEN geological_period IS NOT NULL THEN 1 ELSE 0 END
      + CASE WHEN paleo_latitude   IS NOT NULL
              AND paleo_longitude  IS NOT NULL THEN 1 ELSE 0 END
    )                                                           AS quality_score
FROM occurrences