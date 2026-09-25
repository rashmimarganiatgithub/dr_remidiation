# DR Code Scanning Checklist
 
Source: internal Disaster Recovery (DR) checklist. `zone` rules are added by this skill and are not in the original document.
 
Every rule has a stable `rule_id` used in findings.
 
## 1. Python — Airflow DAG files (`dags/**/*.py`)
 
| rule_id | Area | Detect |
|---|---|---|
| `DR-DAG-PROJECT-01` | Project configuration | Hardcoded GCP project identifiers: `project=`, `project_id=`, `--project`, `--project_id`, or literal project strings passed to operators or clients |
| `DR-DAG-REGION-01` | Region / Location | Explicit region or location values (`us-central1`, `europe-west4`, `US`, `EU`, `us`, `eu`) in DAGs, operators, or task parameters |
| `DR-DAG-ZONE-01` | Zone *(added)* | Explicit zone values matching `<region>-<a..f>` (for example `us-central1-a`, `europe-west4-b`) or literal `zone=`, `--zone` flags |
| `DR-DAG-GCS-01` | GCS bucket refs | Literal bucket names or full `gs://` URIs embedded in DAG logic |
| `DR-DAG-BQ-01` | BigQuery config | Hardcoded dataset, table, or BigQuery job `location=` in DAG code |
| `DR-DAG-BASH-01` | BashOperator | Inline `gcloud`, `bq`, or `gsutil` commands with fixed project/region/zone/dataset/bucket |
| `DR-DAG-VAR-01` | Airflow Variables | `Variable.get("<key>", default_var=...)` where the key or default is environment-specific (contains `prod`, `dev`, region, zone) |
| `DR-DAG-ENV-01` | Env defaults | `os.getenv("<KEY>", "<literal>")` where the literal encodes a project, region, zone, bucket, or dataset |
| `DR-DAG-CRUN-01` | Cloud Run function | Literal Cloud Run function URLs or fully qualified `projects/.../locations/.../services/...` names |
| `DR-DAG-SM-01` | Secret Manager | Literal `projects/<p>/secrets/<name>` or `secretmanager.SecretManagerServiceClient` calls with hardcoded resource paths |
 
## 2. Python — Shared / Common modules
 
| rule_id | Area | Detect |
|---|---|---|
| `DR-COM-CONST-01` | Global constants | Module-level constants defining project IDs, regions, zones, datasets, buckets, or KMS keys |
| `DR-COM-CLIENT-01` | Client init | GCP clients (`bigquery.Client()`, `storage.Client()`, `secretmanager.SecretManagerServiceClient()`) instantiated at import time instead of injected at runtime |
| `DR-COM-HIDDEN-01` | Hidden GCP calls | Utility functions that call GCP services without explicit `project`, `location`, `region`, or `zone` parameters |
| `DR-COM-GCSPATH-01` | GCS path construction | Hardcoded bucket names or paths assembled inside helper functions |
| `DR-COM-SQL-01` | SQL construction | SQL fragments with embedded dataset or table references built from string concatenation or f-strings |
 
## 3. SQL files (`**/*.sql`)
 
| rule_id | Area | Detect |
|---|---|---|
| `DR-SQL-FQT-01` | Fully qualified tables | Direct `<project>.<dataset>.<table>` in `FROM`, `JOIN`, `INSERT INTO`, `UPDATE`, `MERGE` |
| `DR-SQL-DS-01` | Dataset binding | Static dataset names used without parameterization |
| `DR-SQL-GCS-01` | External data sources | `gs://` URIs in `CREATE EXTERNAL TABLE`, `LOAD DATA`, `EXPORT DATA` |
| `DR-SQL-REGION-01` | Region-scoped metadata | `region-<x>.INFORMATION_SCHEMA.*` or region-specific system tables |
 
## 4. Configuration files — JSON (`**/*.json`)
 
| rule_id | Area | Detect |
|---|---|---|
| `DR-CFG-PROJECT-01` | Project identifiers | Static `project`, `project_id`, `gcp_project` keys with literal values |
| `DR-CFG-REGION-01` | Region / Location fields | Explicit `region`, `location` keys with literal region values |
| `DR-CFG-ZONE-01` | Zone fields *(added)* | Explicit `zone`, `default_zone` keys with literal zone values |
| `DR-CFG-GCS-01` | GCS buckets | Bucket names in `bucket`, `bucket_name`, `dag_bucket`, `gcs_prefix` keys |
| `DR-CFG-COMPOSER-01` | Composer / Airflow | Composer environment names, DAG bucket names, env-specific settings |
| `DR-CFG-CI-01` | CI/CD | Deployment YAML/JSON with hardcoded `gcloud`, `bq`, `gsutil` flags |
 
## 5. Shell scripts (`**/*.sh`)
 
| rule_id | Area | Detect |
|---|---|---|
| `DR-SH-GCLOUD-01` | gcloud config | `gcloud config set project <literal>`, `gcloud config set compute/region <literal>`, `gcloud config set compute/zone <literal>` |
| `DR-SH-BQ-01` | BigQuery CLI | `bq --project_id=`, `bq --location=`, `bq mk` with fixed dataset |
| `DR-SH-GSUTIL-01` | GCS CLI | `gsutil` commands with static bucket names or `gs://` paths |
 
## 6. Key Management Service (KMS)
 
| rule_id | Area | Detect |
|---|---|---|
| `DR-KMS-PATH-01` | Key resource paths | Full `projects/<p>/locations/<l>/keyRings/<r>/cryptoKeys/<k>` in code or config |
| `DR-KMS-LOC-01` | Key location | Single-region key locations (any `locations/<region>` that is not `global` or a multi-region) |
| `DR-KMS-RING-01` | Key ring naming | Ring names encoding environment (`prod`, `dev`) or region (`us-central1-ring`) |
| `DR-KMS-CMEK-01` | CMEK refs | CMEK references used by GCS, BigQuery, or Pub/Sub with a single-region key |
 
## Severity assignment
 
- `critical`: hardcoded value blocks failover to alt region/zone (project, region, zone literals, single-region KMS key, `region-<x>.INFORMATION_SCHEMA`).
- `major`: hardcoded value requires code change to migrate (buckets, datasets, fully qualified tables, CI/CD flags).
- `minor`: environment defaults that would still work in DR but hide DR-relevant config (env-specific Airflow Variable names).
 
