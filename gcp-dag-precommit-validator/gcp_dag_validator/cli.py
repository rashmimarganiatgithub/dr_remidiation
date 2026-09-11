# gcp_dag_validator/cli.py
import argparse
import sys
import os
from gcp_dag_validator.core.rule_engine import evaluate_file
from gcp_dag_validator.core.llm_remediator import run_llm_remediator_for_file

from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

console = Console()
ALLOWED_EXTENSIONS = ('.py', '.sql', '.sh', '.json')

def scan_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        console.print(f"[yellow][WARN] Could not read {filepath}: {e}[/yellow]")
        return None, []

    if len(content.encode('utf-8')) > 500 * 1024:
        console.print(f"[dim][SKIP] {filepath} (File > 500KB)[/dim]")
        return None, []

    violations = evaluate_file(filepath, content)
    real_violations = [v for v in violations if v['status'] == 'FAIL']
    
    return content, real_violations

def scan_target(target_path):
    all_issues = {}
    scanned_files = 0

    if os.path.isfile(target_path):
        if target_path.endswith(ALLOWED_EXTENSIONS):
            scanned_files += 1
            content, violations = scan_file(target_path)
            if violations:
                all_issues[target_path] = {"content": content, "violations": violations}
    elif os.path.isdir(target_path):
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'venv', 'env', 'egg-info', 'dist', 'build')]
            for file in files:
                if file.endswith(ALLOWED_EXTENSIONS):
                    filepath = os.path.join(root, file)
                    scanned_files += 1
                    content, violations = scan_file(filepath)
                    if violations:
                        all_issues[filepath] = {"content": content, "violations": violations}

    return scanned_files, all_issues

def print_summary_table(all_issues):
    table = Table(
        title="\nGCP DAG Validator - Static Code Analysis", 
        show_header=True, 
        header_style="bold magenta", 
        expand=True, 
        border_style="dim"
    )
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Line", justify="right", style="dim")
    table.add_column("Rule ID", style="bold red")
    table.add_column("Violation", style="white")
    table.add_column("Code Snippet", style="dim", max_width=40)

    for filepath, data in all_issues.items():
        filename = os.path.basename(filepath)
        
        # Group violations by line number to consolidate multi-violation lines
        line_groups = {}
        for v in data["violations"]:
            line_str = str(v['line_number'])
            if line_str not in line_groups:
                line_groups[line_str] = []
            line_groups[line_str].append(v)
            
        for line in sorted(line_groups.keys(), key=lambda x: int(x) if str(x).isdigit() else 9999):
            v_list = line_groups[line]
            rule_ids = "\n".join([v['rule_id'] for v in v_list])
            rule_names = "\n".join([v['rule_name'] for v in v_list])
            
            snippet = v_list[0]['code_snippet'].strip()
            if len(snippet) > 40:
                snippet = snippet[:37] + "..."
                
            table.add_row(filename, line, rule_ids, rule_names, snippet)

    total_violations = sum(len(d['violations']) for d in all_issues.values())
    console.print(table)    
    return total_violations

def main():
    parser = argparse.ArgumentParser(description="Enterprise GCP DAG Compliance Validator")
    parser.add_argument("paths", nargs="*", default=["."], help="Files or directories to scan")
    args = parser.parse_args()

    total_files_scanned = 0
    all_issues = {}

    with console.status("[bold cyan]Scanning repository...", spinner="line"):
        for path in args.paths:
            if not os.path.exists(path):
                continue
            scanned, issues = scan_target(path)
            total_files_scanned += scanned
            all_issues.update(issues)

    if not all_issues:
        console.print(f"\n[bold green][SYSTEM] Scan complete. Evaluated {total_files_scanned} files. Zero violations found.[/bold green]")
        sys.exit(0)

    total_violations = print_summary_table(all_issues)
    console.print(f"\n[bold red][SYSTEM] Found {total_violations} compliance violation(s) across {len(all_issues)} file(s).[/bold red]\n")

    if Confirm.ask("[bold white]Would you like LLM Dag Remediator to suggest and apply fixes?[/bold white]", default=True):
        
        for filepath, data in all_issues.items():
            
            run_llm_remediator_for_file(filepath, data["content"], data["violations"])

    console.print("\n[bold yellow][SYSTEM] Please review applied fixes, run `git add`, and commit again.[/bold yellow]")
    sys.exit(1)

if __name__ == "__main__":
    main()