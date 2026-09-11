from airflow import DAG
from airflow.models import Variable
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from datetime import datetime
import os

# ❌ VIOLATION (DAG-PY-001): Top-level Variable.get() usage causes scheduler delays[cite: 187].
DB_CONFIG = Variable.get("global_db_config") 

# ❌ VIOLATION (DAG-PY-003): Hardcoded Env Fallback (os.getenv) to a specific region[cite: 188, 189].
ENV = os.environ.get("ENV", "us-central1") 

# ❌ VIOLATION (DAG-GEN-001): Hardcoded Production Project ID[cite: 183].
PROJECT_ID = "dmgcp-del-181" 

# ❌ VIOLATION (DAG-GEN-002): Explicit explicit region or location value.
REGION = "us-central1"

# ❌ VIOLATION (DAG-GEN-003): Hardcoded GCS URI embedded directly in the DAG logic.
OUTPUT_PATH = "gs://prod-billing-bucket/data/" 

# ❌ VIOLATION (DAG-BQ-001): Fully Qualified BQ Tables with embedded project/dataset references[cite: 8, 185].
QUERY = f"SELECT * FROM `{PROJECT_ID}.prod_dataset.users`" 

default_args = {'owner': 'data-eng', 'start_date': datetime(2026, 1, 1)}

with DAG('failing_dr_dag', default_args=default_args, schedule_interval='@daily') as dag:
    start_task = EmptyOperator(task_id='start')