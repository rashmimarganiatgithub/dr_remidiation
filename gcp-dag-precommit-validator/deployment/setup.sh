#!/bin/bash
set -e

# Automatically navigate to the deployment/ folder 
cd "$(dirname "$0")"

echo "====================================================="
echo " Deploying Pre-Commit Python Package to GCP Artifact Registry"
echo "====================================================="

# 1. Dynamically find the correct Python command
if python -c "print('ok')" &> /dev/null; then
    PY_CMD="python"
elif python3 -c "print('ok')" &> /dev/null; then
    PY_CMD="python3"
elif py -c "print('ok')" &> /dev/null; then
    PY_CMD="py"
else
    echo "ERROR: Python is not recognized. Please ensure Python is installed and in your PATH."
    exit 1
fi

echo "-> Detected Python interpreter: $PY_CMD"

# 2. Parse vars.yaml securely
PROJECT_ID=$($PY_CMD -c 'import yaml; print(yaml.safe_load(open("vars.yaml"))["project_id"])')
REGION=$($PY_CMD -c 'import yaml; print(yaml.safe_load(open("vars.yaml"))["region"])')
REPO_NAME=$($PY_CMD -c 'import yaml; print(yaml.safe_load(open("vars.yaml"))["artifact_repo_name"])')

echo "[1/4] Provisioning Python Artifact Registry & Enabling Vuln Scanning via Terraform..."
terraform init
terraform apply -auto-approve \
  -var="project_id=${PROJECT_ID}" \
  -var="region=${REGION}" \
  -var="artifact_repo_name=${REPO_NAME}"

echo "[2/4] Installing build tools (twine & keyring)..."
$PY_CMD -m pip install --upgrade pip build twine keyrings.google-artifactregistry-auth pyyaml

echo "[3/4] Building the Python Package..."
cd .. # Go to the root of the precommit project (gcp-dag-precommit-validator)

# CRITICAL FIX FOR WINDOWS [WinError 5]: 
# Using Python's shutil to force delete directories, bypassing Windows Git Bash locking issues.
echo "-> Safely cleaning old build artifacts..."
$PY_CMD -c "import shutil, os; [shutil.rmtree(d, ignore_errors=True) for d in ['dist', 'build', 'gcp_dag_validator.egg-info'] if os.path.exists(d)]"

$PY_CMD -m build

echo "[4/4] Authenticating and Pushing to GCP Artifact Registry..."
# Twine will now successfully upload Version 1.0.2
twine upload \
    --repository-url https://${REGION}-python.pkg.dev/${PROJECT_ID}/${REPO_NAME}/ \
    dist/*

echo "====================================================="
echo "Deployment Complete! The pre-commit hook is now available in Artifact Registry."
echo "====================================================="