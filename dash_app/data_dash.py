"""Loads the fossil occurrence dataset from BigQuery."""

from functools import lru_cache
from google.cloud import bigquery


@lru_cache(maxsize=1)
def load_occurrences():
    """Run the BigQuery query once, cache,  and return the result as a pandas DataFrame.

    Args:
        None.

    Returns:
        pandas.DataFrame: one row per fossil occurrence, with all columns
        from the marts.fact_occurrences table (taxon_name, discovery_year,
        geological_epoch, modern_latitude/longitude, etc.).
    """
    client = bigquery.Client(project='dinosauria-499515')  
    query = 'SELECT * FROM `dinosauria-499515.marts.fact_occurrences`' 
    return client.query(query).to_dataframe()  
