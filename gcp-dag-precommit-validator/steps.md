
# Authenticate your local terminal with GCP
gcloud auth login
gcloud auth application-default login


# Install the Artifact Registry auth helper & pre-commit for pip
pip install keyrings.google-artifactregistry-auth pre-commit


# install precommit-dag-scanner package
pip install --index-url https://us-central1-python.pkg.dev/dmgcp-del-181/python-precommit-repo/simple/ gcp-dag-validator==2.1.6


######################
# TEST
######################

git add *
git commit -m "test: commit fail_dag.py"