# gcp-dag-precommit-validator/deployment/main.tf

variable "project_id" {}
variable "region" {}
variable "artifact_repo_name" {}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Enable the Container Scanning API for Vulnerability Detection
resource "google_project_service" "container_scanning" {
  project            = var.project_id
  service            = "containerscanning.googleapis.com"
  disable_on_destroy = false
}

# 2. Provision the Python Artifact Registry
resource "google_artifact_registry_repository" "python_repo" {
  location      = var.region
  repository_id = var.artifact_repo_name
  description   = "Internal Python Package Repo for Pre-Commit Hooks"
  format        = "PYTHON"

  depends_on = [google_project_service.container_scanning]
}