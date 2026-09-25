#!/usr/bin/env python3
import sys
import re
from pathlib import Path

# DR Compliance regex auto-remediation rules
PYTHON_REPLACEMENTS = [
    # Hardcoded project_id variable assignments -> os.getenv("PROJECT_ID")
    (
        r'(?i)(project_id\s*[:=]\s*)[\'"][a-z0-9-]+[\'"]',
        r'\1os.getenv("PROJECT_ID")'
    ),
    # Hardcoded GCP region/location strings -> os.getenv("COMPOSER_LOCATION")
    (
        r'[\'"](us-central1|us-east4|europe-west1|asia-south1|us-west1)[\'"]',
        'os.getenv("COMPOSER_LOCATION")'
    ),
    # Hardcoded GCS bucket URIs -> os.getenv("GCS_BUCKET_URI")
    (
        r'[\'"]gs://[a-z0-9_\.-]+(/[^\'"]*)?[\'"]',
        'os.getenv("GCS_BUCKET_URI")'
    ),
    # Hardcoded fully qualified BigQuery tables `project.dataset.table` -> os.getenv("BQ_TABLE_REF")
    (
        r'`[a-z0-9-]+`\.`[a-z0-9_]+`\.`[a-z0-9_]+`',
        'os.getenv("BQ_TABLE_REF")'
    ),
    # Fallback default regions inside os.getenv calls
    (
        r'(?i)(os\.environ\.get|os\.getenv)\(([^,]+),\s*[\'"](prod|us-central1|us-east4)[\'"]\)',
        r'\1(\2)'
    )
]

SHELL_REPLACEMENTS = [
    (r'(?i)--project[= ][\'"]?[a-z0-9-]+[\'"]?', '--project="${PROJECT_ID}"'),
    (r'(?i)--location[= ][\'"]?[a-z]+-[a-z]+[0-9][\'"]?', '--location="${COMPOSER_LOCATION}"'),
    (r'[\'"]gs://[a-z0-9_\.-]+(/[^\'"]*)?[\'"]', '"gs://${GCS_BUCKET_NAME}"'),
]

def remediate_python_file(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    modified = content

    for pattern, replacement in PYTHON_REPLACEMENTS:
        modified = re.sub(pattern, replacement, modified)

    # Automatically inject 'import os' if os.getenv was added and missing
    if ("os.getenv" in modified or "os.environ" in modified) and not re.search(r'^\s*(import os|from os import)', modified, re.MULTILINE):
        modified = "import os\n" + modified

    if modified != content:
        path.write_text(modified, encoding="utf-8")
        return True
    return False

def remediate_generic_file(path: Path, replacements: list) -> bool:
    content = path.read_text(encoding="utf-8")
    modified = content

    for pattern, replacement in replacements:
        modified = re.sub(pattern, replacement, modified)

    if modified != content:
        path.write_text(modified, encoding="utf-8")
        return True
    return False

def remediate_file(file_path: str):
    path = Path(file_path)
    if not path.exists():
        print(f"File not found: {file_path}")
        return

    ext = path.suffix.lower()
    changed = False

    if ext == ".py":
        changed = remediate_python_file(path)
    elif ext in [".sh", ".bash"]:
        changed = remediate_generic_file(path, SHELL_REPLACEMENTS)
    else:
        changed = remediate_generic_file(path, PYTHON_REPLACEMENTS)

    if changed:
        print(f"Remediated DR compliance violations in {file_path}")
    else:
        print(f"No automatically fixable violations found in {file_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python remediate_violations.py <file1> <file2> ...")
        sys.exit(1)

    for target_file in sys.argv[1:]:
        remediate_file(target_file)