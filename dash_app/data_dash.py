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


def filter_occurrences(df, discovery_range, selected_epochs, selected_taxa):
    """Filter occurrences by year range, epoch, and optional taxon list.

    Shared by update_map() and the statistics panel so both react to the
    same filters.

    Args:
        df (pandas.DataFrame): occurrence rows, from load_occurrences().
        discovery_range (list[int, int]): [low, high] discovery year.
        selected_epochs (list[str]): epoch names to keep.
        selected_taxa (list[str]): taxon names to keep, or [] for no restriction.

    Returns:
        pandas.DataFrame: the filtered rows.
    """
    filtered = df[
        (df['discovery_year'] >= discovery_range[0]) &
        (df['discovery_year'] <= discovery_range[1]) &
        (df['geological_epoch'].isin(selected_epochs))
    ]
    if selected_taxa:  # empty means no taxon restriction
        filtered = filtered[filtered['taxon_name'].isin(selected_taxa)]
    return filtered
