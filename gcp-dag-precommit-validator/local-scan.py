# local-scan.py
import os
import sys
import argparse
from gcp_dag_validator.core.rule_engine import evaluate_file

# ANSI Colors for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

ALLOWED_EXTENSIONS = ('.py', '.sql', '.sh', '.json')

def scan_file(filepath):
    """Reads and evaluates a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"{YELLOW}[WARN]{RESET} Could not read {filepath}: {e}")
        return 0

    # Skip large data dumps
    if len(content.encode('utf-8')) > 500 * 1024:
        print(f"{YELLOW}[SKIP]{RESET} {filepath} (File > 500KB)")
        return 0

    violations = evaluate_file(filepath, content)
    real_violations = [v for v in violations if v['status'] == 'FAIL']

    if real_violations:
        print(f"\n{RED}{BOLD}FAIL:{RESET} {BOLD}{filepath}{RESET}")
        for v in real_violations:
            print(f"  {RED}Line {v['line_number']}:{RESET} [{v['rule_id']}] {v['rule_name']}")
            print(f"    Snippet: {v['code_snippet'].strip()[:150]}")
        return len(real_violations)
    
    return 0

def scan_target(target_path):
    """Recursively scans a directory or processes a single file."""
    total_violations = 0
    scanned_files = 0

    if os.path.isfile(target_path):
        if target_path.endswith(ALLOWED_EXTENSIONS):
            scanned_files += 1
            total_violations += scan_file(target_path)
    elif os.path.isdir(target_path):
        for root, dirs, files in os.walk(target_path):
            
            # FIX: Modify dirs in-place to skip hidden folders natively
            # This allows relative paths like '../' to work perfectly
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'venv', 'env')]

            for file in files:
                if file.endswith(ALLOWED_EXTENSIONS):
                    filepath = os.path.join(root, file)
                    scanned_files += 1
                    total_violations += scan_file(filepath)

    return scanned_files, total_violations

def main():
    parser = argparse.ArgumentParser(description="Directly scan a directory for GCP DAG Compliance without pip/pre-commit")
    parser.add_argument("target", help="Directory path or file path to scan")
    args = parser.parse_args()

    target = args.target

    if not os.path.exists(target):
        print(f"{RED}Error: Path '{target}' does not exist.{RESET}")
        sys.exit(1)

    print(f"Scanning target: {BOLD}{target}{RESET} ...\n")
    
    scanned_files, total_violations = scan_target(target)
    
    print(f"\n{'-'*50}")
    print(f"Scan complete. Evaluated {scanned_files} files.")
    
    if total_violations > 0:
        print(f"{RED}{BOLD}Found {total_violations} compliance violation(s).{RESET}")
        sys.exit(1)
    else:
        print(f"{GREEN}{BOLD}All files compliant!{RESET}")
        sys.exit(0)

if __name__ == "__main__":
    main()