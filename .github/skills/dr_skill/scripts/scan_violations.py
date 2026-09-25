#!/usr/bin/env python3
import sys
import yaml
import re
import ast
import os
from pathlib import Path

class ASTChecker(ast.NodeVisitor):
    def __init__(self):
        self.findings = []
        self.scope = "module"

    def visit_FunctionDef(self, node):
        prev_scope = self.scope
        self.scope = "function"
        self.generic_visit(node)
        self.scope = prev_scope

    def visit_ClassDef(self, node):
        prev_scope = self.scope
        self.scope = "class"
        self.generic_visit(node)
        self.scope = prev_scope

    def visit_Call(self, node):
        # DAG-PY-001: Top-level Variable.get()
        if self.scope == "module":
            if isinstance(node.func, ast.Attribute):
                if getattr(node.func.value, 'id', '') == 'Variable' and node.func.attr == 'get':
                    self.findings.append(f"Line {node.lineno}: Top-Level Variable.get() usage")
            
            # DAG-PY-002: Early GCP Client Initialization
            if isinstance(node.func, ast.Attribute) and node.func.attr == 'Client':
                if getattr(node.func.value, 'id', '') in ['storage', 'bigquery', 'secretmanager']:
                    self.findings.append(f"Line {node.lineno}: Early GCP Client Initialization at module level")
        
        self.generic_visit(node)

def load_rules(rules_path):
    with open(rules_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f).get('rules', [])

def scan_file(file_path, rules):
    ext = Path(file_path).suffix
    findings = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()
    except Exception as e:
        return [f"Error reading file {file_path}: {e}"]

    # 1. Regex checks
    for rule in rules:
        if rule.get('type') == 'regex' and ext in rule.get('extensions', []):
            pattern = re.compile(rule['pattern'], re.IGNORECASE)
            for idx, line in enumerate(lines):
                if pattern.search(line):
                    findings.append(f"[{rule['id']}] {rule['name']} at line {idx+1}: {line.strip()}")

    # 2. AST checks (Python only)
    if ext == '.py':
        ast_rules = [r for r in rules if r.get('type') == 'ast']
        if ast_rules:
            try:
                tree = ast.parse(content)
                checker = ASTChecker()
                checker.visit(tree)
                for finding in checker.findings:
                    findings.append(f"[AST-Violation] {finding}")
            except SyntaxError as e:
                findings.append(f"Syntax error during AST parse: {e}")

    return findings

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scan_violations.py <file1> <file2> ...")
        sys.exit(1)

    script_dir = Path(__file__).parent
    rules_path = script_dir.parent / 'references' / 'dag_rules.yaml'
    
    if not rules_path.exists():
        print(f"Error: Rules file not found at {rules_path}")
        sys.exit(1)

    rules = load_rules(rules_path)
    files_to_scan = sys.argv[1:]
    
    total_findings = 0
    for file_path in files_to_scan:
        if not os.path.exists(file_path):
            continue
        
        issues = scan_file(file_path, rules)
        if issues:
            print(f"\n--- Violations in {file_path} ---")
            for issue in issues:
                print(issue)
                total_findings += 1

    if total_findings > 0:
        sys.exit(1)
    else:
        print("\nNo DR compliance violations found.")
        sys.exit(0)
