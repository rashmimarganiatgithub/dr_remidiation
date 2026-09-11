from airflow import DAG
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from datetime import datetime

with DAG('bq_daily_load', start_date=datetime(2026, 1, 1), schedule_interval='@daily', catchup=False) as dag:
    
    run_query = BigQueryInsertJobOperator(
        task_id='run_query',
        # ✅ FIXED: Uses native Airflow Jinja templating for operator arguments
        project_id='{{ var.value.dr_project_id }}', 
        location='{{ var.value.dr_region }}', 
        configuration={
            "query": {
                # ✅ FIXED: BQ Table parameterized using Jinja syntax inside the query
                "query": "SELECT * FROM `{{ var.value.dr_project_id }}.{{ var.value.dr_dataset }}.transactions` WHERE amount > 100",
                "useLegacySql": False,
            }
        }
    )