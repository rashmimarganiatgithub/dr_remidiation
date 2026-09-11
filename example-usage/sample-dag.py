from airflow import DAG
from airflow.models import Variable
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from datetime import datetime
import os

# def _execute_compliant_task(**kwargs):
#     """
#     ✅ COMPLIANT: Variables are fetched at runtime within the callable context. 
#     This prevents scheduler timeouts and dynamically adjusts during a DR failover event.
#     """
#     db_config = Variable.get("global_db_config")
    
#     # ✅ COMPLIANT: Project IDs and Regions are fetched dynamically via Airflow Variables.
#     project_id = Variable.get("gcp_project_id")
#     region = Variable.get("gcp_region")
    
#     # ✅ COMPLIANT: GCS URIs are constructed dynamically.
#     gcs_bucket = Variable.get("billing_output_bucket")
#     output_path = f"gs://{gcs_bucket}/data/"
    
#     # ✅ COMPLIANT: BigQuery queries use parameterized dataset references.
#     dataset = Variable.get("bq_prod_dataset")
#     query = f"SELECT * FROM `{project_id}.{dataset}.users`"
    
#     print(f"Running task in {region} for project {project_id}")

default_args = {'owner': 'data-eng', 'start_date': datetime(2026, 1, 1)}

with DAG('compliant_dr_dag', default_args=default_args, schedule_interval='@daily') as dag:
    start_task = EmptyOperator(task_id='start') 
    
    process_task = PythonOperator(
        task_id='process_data',
        python_callable=_execute_compliant_task
    )
    
    start_task >> process_task