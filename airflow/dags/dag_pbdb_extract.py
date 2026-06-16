from datetime import datetime
import requests
import json
import os

from airflow import DAG
from airflow.operators.python import PythonOperator

from google.cloud import storage
from google.cloud import bigquery

PBDB_URL = 'https://paleobiodb.org/data1.2/occs/list.json?base_name=Dinosauria&show=coords,paleoloc,classext,attr,loc,ref&limit=all'
NDJSON_PATH = '/tmp/pbdb_dinosauria_raw.ndjson'
GCP_PROJECT = 'dinosauria-499515'
BQ_TABLE_ID = f'{GCP_PROJECT}.bronze.pbdb_dinosauria_raw'
BUCKET = 'dinosauria-discovery-raw'

def fetch_and_export():
    response = requests.get(PBDB_URL, timeout=60)
    response.raise_for_status()
    data = response.json()
    records = data['records']
    
    with open(NDJSON_PATH, 'w') as f:
        for record in records:
            str_record = {k: str(v) if v is not None else None for k, v in record.items()}
            f.write(json.dumps(str_record) + '\n')

    print(f"Fetched and exported {len(records)} records to {NDJSON_PATH}")
    return NDJSON_PATH

def upload_to_gcs(**kwargs):
    ti = kwargs['ti']
    filepath = ti.xcom_pull(task_ids='fetch_and_export')
    
    client = storage.Client()
    bucket = client.bucket(BUCKET)
    blob = bucket.blob(os.path.basename(filepath))
    blob.upload_from_filename(filepath)
    return f"gs://{BUCKET}/{os.path.basename(filepath)}"

def ingest_bq(**kwargs):
    ti = kwargs['ti']
    gcs_uri = ti.xcom_pull(task_ids='upload_to_gcs')
    
    client = bigquery.Client(project=GCP_PROJECT)
    config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    job = client.load_table_from_uri(gcs_uri, BQ_TABLE_ID, job_config=config)
    job.result()

with DAG(
    dag_id='pbdb_extract',
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False
) as dag:

    task_fetch = PythonOperator(
        task_id='fetch_and_export',
        python_callable=fetch_and_export,
    )
    task_upload = PythonOperator(
        task_id='upload_to_gcs',
        python_callable=upload_to_gcs,
    )
    task_ingest = PythonOperator(
        task_id='ingest_bq',
        python_callable=ingest_bq,
    )
    
    task_fetch >> task_upload >> task_ingest
