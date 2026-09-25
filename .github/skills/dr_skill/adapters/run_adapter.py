#!/usr/bin/env python3
import sys
import os
import subprocess
from pathlib import Path

ADAPTER_DIR = Path(__file__).resolve().parent
DR_ROOT = ADAPTER_DIR.parent
SKILL_FILE = DR_ROOT / "SKILL.md"
SCANNER = DR_ROOT / "scripts" / "scan_violations.py"
REMEDIATOR = DR_ROOT / "scripts" / "remediate_violations.py"

def run_cmd(cmd_args):
    return subprocess.run(cmd_args, capture_output=False).returncode

def main():
    files = sys.argv[1:]
    if not files:
        sys.exit(0)

    # Validates SKILL.md presence as the primary skill driver
    if not SKILL_FILE.exists():
        print(f"Error: SKILL.md entrypoint not found at {SKILL_FILE}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded DR Remediation Skill from: {SKILL_FILE.name}")

    #Runs Scanner Script
    print("Executing DR Compliance Scanner...")
    scan_code = run_cmd([sys.executable, str(SCANNER)] + files)

    if scan_code == 0:
        print("DR Compliance check passed.")
        sys.exit(0)

    # Runs Rule-Based Remediator Script (No LLM / API key required)
    print("Violations found. Executing rule-based auto-remediation...")
    run_cmd([sys.executable, str(REMEDIATOR)] + files)

    #  Re-verify compliance
    print("Re-scanning modified files...")
    re_scan_code = run_cmd([sys.executable, str(SCANNER)] + files)

    if re_scan_code == 0:
        print("Remediation successful.")
        sys.exit(0)
    else:
        print("Remediation incomplete. Manual intervention required.")
        sys.exit(1)

if __name__ == "__main__":
    main()