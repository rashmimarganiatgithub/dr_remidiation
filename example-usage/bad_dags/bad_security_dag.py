from airflow.decorators import dag, task
from google.cloud import secretmanager
from datetime import datetime

# ❌ VIOLATION (DAG-PY-002): Early GCP Client Initialization
sm_client = secretmanager.SecretManagerServiceClient()

# ❌ VIOLATION (DAG-SEC-001): Hardcoded Secret Manager Path
SECRET_PATH = "projects/dmgcp-del-181/secrets/db_password/versions/latest"

# ❌ VIOLATION (DAG-KMS-001): Hardcoded KMS Resource Path
KMS_KEY = "projects/dmgcp-del-181/locations/us-central1/keyRings/my-ring/cryptoKeys/my-key"


@dag(start_date=datetime(2026, 1, 1), schedule_interval='@daily')
def secure_data_pipeline():

    @task
    def fetch_credentials():
        response = sm_client.access_secret_version(request={"name": SECRET_PATH})
        print(f"Decrypting with {KMS_KEY}...")
        return response.payload.data.decode("UTF-8")

    fetch_credentials()

dag_obj = secure_data_pipeline()