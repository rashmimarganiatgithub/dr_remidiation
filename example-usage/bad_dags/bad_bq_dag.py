from airflow import DAG
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from datetime import datetime

with DAG('bq_daily_load', start_date=datetime(2026, 1, 1), schedule_interval='@daily') as dag:
    
    # ❌ VIOLATION (DAG-GEN-001): Hardcoded Project
    # ❌ VIOLATION (DAG-GEN-002): Hardcoded Location
    run_query = BigQueryInsertJobOperator(
        task_id='run_query',
        project_id='dmgcp-del-181', 
        location='us-central1', 
        configuration={
            "query": {
                # ❌ VIOLATION (DAG-BQ-001): Fully Qualified BQ Table
                "query": "SELECT * FROM `dmgcp-del-181.prod_dataset.transactions` WHERE amount > 100",
                "useLegacySql": False,
            }
        }
    )