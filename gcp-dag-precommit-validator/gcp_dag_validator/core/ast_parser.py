import ast
import warnings

def analyze_ast(filename, code_content, ast_rules):
    results = []
    lines = code_content.split('\n')
        
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=SyntaxWarning)
        try:
            tree = ast.parse(code_content, filename=filename)
        except SyntaxError as e:
            return [{
                "rule_id": "SYS-ERR-001",
                "rule_name": "Valid Python Syntax",
                "status": "FAIL",
                "line_number": getattr(e, 'lineno', 1),
                "code_snippet": str(e)
            }]

    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    
    check_top_level_var = any(r['ast_check'] == 'top_level_variable' for r in ast_rules)
    check_early_client = any(r['ast_check'] == 'early_client_init' for r in ast_rules)

    for node in ast.walk(tree):
        if check_top_level_var and isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == 'get':
                if isinstance(node.func.value, ast.Name) and node.func.value.id == 'Variable':
                    is_top_level = True
                    for func in functions:
                        if hasattr(node, 'lineno') and func.lineno <= node.lineno <= func.end_lineno:
                            is_top_level = False
                            break
                    if is_top_level:
                        rule = next(r for r in ast_rules if r['ast_check'] == 'top_level_variable')
                        results.append({
                            "rule_id": rule['id'],
                            "rule_name": rule['name'],
                            "status": "FAIL",
                            "line_number": getattr(node, 'lineno', '-'),
                            "code_snippet": lines[node.lineno - 1].strip() if hasattr(node, 'lineno') else str(node)
                        })

        if check_early_client and isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == 'Client':
                is_top_level = True
                for func in functions:
                    if hasattr(node, 'lineno') and func.lineno <= node.lineno <= func.end_lineno:
                        is_top_level = False
                        break
                if is_top_level:
                    rule = next(r for r in ast_rules if r['ast_check'] == 'early_client_init')
                    results.append({
                        "rule_id": rule['id'],
                        "rule_name": rule['name'],
                        "status": "FAIL",
                        "line_number": getattr(node, 'lineno', '-'),
                        "code_snippet": lines[node.lineno - 1].strip() if hasattr(node, 'lineno') else str(node)
                    })

    return results