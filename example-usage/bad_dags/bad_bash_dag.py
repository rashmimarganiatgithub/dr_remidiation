from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG('bash_deploy_dag', start_date=datetime(2026, 1, 1), schedule_interval='@daily') as dag:
    
    deploy_model = BashOperator(
        task_id='deploy_model',
        # ❌ VIOLATION (DAG-GEN-003): Hardcoded GCS Bucket
        # ❌ VIOLATION (DAG-GEN-002): Hardcoded Region
        # ❌ VIOLATION (DAG-GEN-001): Hardcoded Project ID
        bash_command="""
            gsutil cp gs://prod-ml-models-bucket/v1/model.pkl .
            gcloud run deploy my-model-api \
                --image gcr.io/dmgcp-del-181/model:latest \
                --region us-central1 \
                --project dmgcp-del-181
        """
        LOCATION = "us-east1-a"
        GCS_BUCKET = "gs://my-production-bucket-data1"
    )