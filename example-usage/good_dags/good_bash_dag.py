from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG('bash_deploy_dag', start_date=datetime(2026, 1, 1), schedule_interval='@daily', catchup=False) as dag:
    
    # ✅ FIXED: Multi-line bash string is retained, but fixed values are 
    # replaced with Airflow Jinja templating so they swap during DR failover.
    deploy_model = BashOperator(
        task_id='deploy_model',
        bash_command="""
            gsutil cp {{ var.value.model_gcs_uri }}/model.pkl .
            gcloud run deploy my-model-api \
                --image {{ var.value.artifact_registry_image }} \
                --region {{ var.value.dr_region }} \
                --project {{ var.value.dr_project_id }}
        """
    )