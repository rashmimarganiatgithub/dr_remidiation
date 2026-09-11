from airflow.decorators import dag, task
from airflow.models import Variable
from datetime import datetime

@dag(start_date=datetime(2026, 1, 1), schedule_interval='@daily', catchup=False)
def secure_data_pipeline():

    @task
    def fetch_credentials():
        # ✅ FIXED: Client initialization is moved INSIDE the execution context.
        # It will now only fire when the task actually runs, saving scheduler CPU.
        from google.cloud import secretmanager
        sm_client = secretmanager.SecretManagerServiceClient()
        
        # ✅ FIXED: Hardcoded paths replaced with dynamic Variables inside the task
        secret_path = Variable.get("db_secret_path")
        kms_key = Variable.get("dr_kms_key_path")
        
        response = sm_client.access_secret_version(request={"name": secret_path})
        print(f"Decrypting with {kms_key}...")
        return response.payload.data.decode("UTF-8")

    fetch_credentials()

dag_obj = secure_data_pipeline()
