import streamlit as st
from google.cloud import bigquery


@st.cache_data # stores result after first call
def load_occurrences():
    client = bigquery.Client(project='dinosauria-499515')
    query = 'SELECT * FROM `dinosauria-499515.marts.fact_occurrences`'
    return client.query(query).to_dataframe()