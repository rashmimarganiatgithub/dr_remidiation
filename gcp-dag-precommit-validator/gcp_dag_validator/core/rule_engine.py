import yaml
import re
import os
from gcp_dag_validator.core.ast_parser import analyze_ast

def load_rules():
    # Dynamically find the rules file relative to this module's installed location
    rules_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'rules', 'dag_rules.yaml')
    try:
        with open(rules_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f).get('rules', [])
    except FileNotFoundError:
        print(f"[ERROR] Rule file not found at {rules_path}")
        return []

RULES = load_rules()

def evaluate_file(filename, content):
    violations = []
    file_ext = os.path.splitext(filename)[1].lower()
    lines = content.split('\n')

    for rule in RULES:
        if rule['type'] == 'regex' and file_ext in rule.get('extensions', []):
            pattern = re.compile(rule['pattern'])
            for i, line in enumerate(lines):
                stripped_line = line.strip()
                
                # ==========================================
                # FIX: IGNORE COMMENTED AND EMPTY LINES
                # ==========================================
                if not stripped_line:
                    continue
                if file_ext in ['.py', '.sh'] and stripped_line.startswith('#'):
                    continue
                if file_ext == '.sql' and (stripped_line.startswith('--') or stripped_line.startswith('#')):
                    continue
                if file_ext == '.json' and stripped_line.startswith('//'):
                    continue
                # ==========================================
                
                if pattern.search(line):
                    violations.append({
                        "rule_id": rule['id'],
                        "rule_name": rule['name'],
                        "status": "FAIL",
                        "line_number": i + 1,
                        "code_snippet": line.strip()[:1000] 
                    })

    if file_ext == '.py':
        ast_rules = [r for r in RULES if r['type'] == 'ast']
        if ast_rules:
            ast_violations = analyze_ast(filename, content, ast_rules)
            violations.extend(ast_violations)

    if not violations:
        violations.append({
            "rule_id": "SYS-COMPLIANT",
            "rule_name": "Passed all applicable DAG Policies",
            "status": "PASS",
            "line_number": "-",
            "code_snippet": "-"
        })

    return violations