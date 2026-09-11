# gcp_dag_validator/core/llm_remediator.py
import os
import subprocess
import platform
import warnings
import json
import difflib
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Confirm, Prompt
from rich.table import Table

warnings.filterwarnings("ignore", module="vertexai")

console = Console()

# =====================================================================
# STATEFUL SESSION CACHE 
# Stores user mappings (e.g., 'dmgcp-del-181' -> 'dr_project_id') across files
# =====================================================================
GLOBAL_MAPPING_CACHE = {}

def get_smart_gcp_project():
    """Smartly resolves the GCP project for Vertex AI billing/quota."""
    proj = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if proj:
        return proj
    
    try:
        gcloud_cmd = "gcloud.cmd" if platform.system() == "Windows" else "gcloud"
        result = subprocess.run(
            [gcloud_cmd, "config", "get-value", "project"], 
            capture_output=True, text=True, check=True
        )
        proj = result.stdout.strip()
        if proj:
            return proj
    except Exception:
        pass
    
    return None

def calculate_diff_stats_and_lines(original, new):
    """Calculates lines added/removed and identifies the specific line numbers modified."""
    diff = list(difflib.ndiff(original.splitlines(), new.splitlines()))
    added = 0
    removed = 0
    new_line_num = 0
    changed_lines = set()

    for line in diff:
        if line.startswith('  '):
            new_line_num += 1
        elif line.startswith('+ '):
            added += 1
            new_line_num += 1
            changed_lines.add(new_line_num)
        elif line.startswith('- '):
            removed += 1

    return added, removed, changed_lines

def clean_json_response(raw_text):
    """Safely extracts JSON from LLM response, handling potential markdown wrappers."""
    raw_text = raw_text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:-3].strip()
    elif raw_text.startswith("```"):
        raw_text = raw_text[3:-3].strip()
    return json.loads(raw_text)

def run_llm_remediator_for_file(filepath, original_content, violations):
    global GLOBAL_MAPPING_CACHE

    # 1. IMMEDIATE feedback before any processing starts
    console.print(f"\n[bold cyan][llm-remediator] Initiating Bulk File Remediation for {filepath}[/bold cyan]")
    
    # 2. Wrap the heavy imports and gcloud subprocess in a loading spinner
    with console.status("[dim]Authenticating GCP Context & Booting AI Engine...[/dim]", spinner="dots"):
        import vertexai
        from vertexai.generative_models import GenerativeModel, GenerationConfig
        
        project_id = get_smart_gcp_project()

    if not project_id:
        console.print("[bold yellow][SYSTEM] llm-remediator skipped: Cannot determine active GCP Project.[/bold yellow]")
        return 0, 0, 0

    ext = os.path.splitext(filepath)[1].lower()
    file_type_map = {'.py': 'python', '.sql': 'sql', '.sh': 'bash', '.json': 'json'}
    lang = file_type_map.get(ext, 'text')

    try:
        vertexai.init(project=project_id, location="global")
        
        generation_config = GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1
        )
        
        model = GenerativeModel("gemini-3.5-flash", generation_config=generation_config) 
        chat = model.start_chat()

        violations_str = "\n".join([f"- Line {v['line_number']}: [{v['rule_id']}] {v['rule_name']} -> {v['code_snippet'].strip()}" for v in violations])
        
        # =====================================================================
        # PHASE 1: File-Level Context & Variable Extraction
        # =====================================================================
        prompt = f"""
        You are an Enterprise GCP Cloud Architect and Data Engineer.
        We are applying Disaster Recovery (DR) compliance fixes to the ENTIRE {lang} file '{filepath}'.
        
        Current File Content:
        ```{lang}
        {original_content}
        ```

        Identified Compliance Violations:
        {violations_str}

        Remediation Strategy:
        We need to replace hardcoded values (Project IDs, Regions, Buckets) with Airflow dynamic configurations.

        YOUR TASK - PHASE 1:
        Scan the file and violations. Identify all hardcoded values that must be parameterized.
        Do NOT hallucinate variable names. If a hardcoded value needs to be replaced, ask the user for the corresponding variable name.

        Respond STRICTLY with this JSON format:
        {{
            "requires_user_inputs": boolean,
            "required_variables": [
                {{
                    "hardcoded_value": "The exact hardcoded string in the code",
                    "context": "Brief description of where/how it is used",
                    "suggested_prompt": "Please provide the Airflow Variable name for ..."
                }}
            ],
            "explanation": "Summary of your analysis",
            "fixed_code": "If requires_user_inputs is false, put the COMPLETE FIXED RAW CODE here. Otherwise, null."
        }}
        """

        with console.status("[dim]Analyzing file architecture & extracting mapping requirements...[/dim]", spinner="line"):
            response = chat.send_message(prompt)
            
        try:
            res_json = clean_json_response(response.text)
        except json.JSONDecodeError as e:
            console.print(f"[bold red][ERROR] Invalid model response. Skipping file. Error: {e}[/bold red]")
            return 0, 0, 0

        # =====================================================================
        # PHASE 2: Bulk User Input Collection (WITH STATEFUL MEMORY)
        # =====================================================================
        user_mappings = {}
        if res_json.get("requires_user_inputs"):
            required_vars = res_json.get("required_variables", [])
            if required_vars:
                console.print(f"\n[bold yellow]Action Required:[/bold yellow] To accurately remediate '{os.path.basename(filepath)}', please provide dynamic variable mappings:")
                
                for req in required_vars:
                    hardcoded_val = req.get("hardcoded_value")
                    question = req.get("suggested_prompt", f"Variable name to replace '{hardcoded_val}'?")
                    context = req.get("context", "Found in codebase")

                    # Check Stateful Cache First
                    if hardcoded_val in GLOBAL_MAPPING_CACHE:
                        cached_var = GLOBAL_MAPPING_CACHE[hardcoded_val]
                        use_cached = Confirm.ask(f"[bold magenta]? Cached Mapping Found:[/bold magenta] Use '{cached_var}' for '{hardcoded_val}'?", default=True)
                        if use_cached:
                            user_mappings[hardcoded_val] = cached_var
                            continue
                    
                    console.print(f"[bold cyan]? {question}[/bold cyan] [dim](Context: {context})[/dim]")
                    user_val = Prompt.ask("[bold white]Your input[/bold white]")
                    
                    # Store in current mapping and update global cache
                    user_mappings[hardcoded_val] = user_val
                    GLOBAL_MAPPING_CACHE[hardcoded_val] = user_val

            # =====================================================================
            # PHASE 3: Bulk Code Generation (WITH STRICT AIRFLOW AST RULES)
            # =====================================================================
            follow_up = f"""
            The user provided the following mapping for the hardcoded values:
            {json.dumps(user_mappings, indent=2)}

            Now, rewrite the ENTIRE file. Apply these CRITICAL AIRFLOW RULES:
            
            1. NO TOP-LEVEL VARIABLES: You MUST NEVER place `Variable.get()` or `os.environ.get()` at the top-level (root) of the DAG file. Doing so crashes the Airflow scheduler.
            2. JINJA TEMPLATING FOR OPERATORS: For standard operators (BigQueryInsertJobOperator, BashOperator, etc.), replace hardcoded strings DIRECTLY inside the operator arguments using Jinja templating. 
               - Correct Example: `project_id="{{{{ var.value.my_var }}}}"`
               - WRONG Example: `project_id=Variable.get("my_var")`
            3. PYTHON CALLABLES: For `@task` decorators or `PythonOperator` callables, you MAY use `Variable.get("my_var")` but it MUST be safely inside the function definition (`def my_func():`).
            4. GCP CLIENTS: Move all `Client()` initializations (e.g., `SecretManagerServiceClient()`) inside the python callables.
            
            Replace the hardcoded values based on the mapping above, strictly obeying the Airflow Rules.

            Respond STRICTLY with this JSON format:
            {{
                "requires_user_inputs": false,
                "explanation": "A concise summary of all applied fixes.",
                "fixed_code": "THE COMPLETE RAW FILE CONTENT HERE WITH ALL FIXES APPLIED. DO NOT TRUNCATE."
            }}
            """
            
            with console.status("[dim]Applying bulk fixes and restructuring code safely...[/dim]", spinner="line"):
                response = chat.send_message(follow_up)
                res_json = clean_json_response(response.text)

        fixed_code = res_json.get("fixed_code")
        explanation = res_json.get("explanation", "Applied bulk DR compliance fixes.")

        if not fixed_code or fixed_code.strip() == original_content.strip():
            console.print("[bold red][ERROR] Model failed to generate valid fixed code, or no changes were required. Skipping.[/bold red]")
            return 0, 0, 0

        # Safely strip markdown code blocks if the LLM hallucinated them inside the JSON string
        fixed_code = fixed_code.strip()
        if fixed_code.startswith("```"):
            fixed_code = "\n".join(fixed_code.split("\n")[1:-1]).strip()

        # =====================================================================
        # PHASE 4: Unified Diff Calculation & Application
        # =====================================================================
        total_added, total_removed, all_changed_lines = calculate_diff_stats_and_lines(original_content, fixed_code)

        console.print(Panel(explanation, title="[bold blue]Proposed File-Level Remediation[/bold blue]", border_style="blue"))

        final_diff_table = Table(show_header=True, header_style="bold cyan", expand=True, border_style="cyan")
        final_diff_table.add_column("Original File", justify="left", style="dim", ratio=1)
        final_diff_table.add_column(f"Fully Fixed File ([bold green]+{total_added}[/bold green] [bold red]-{total_removed}[/bold red])", justify="left", ratio=1)

        final_orig_syntax = Syntax(original_content, lang, theme="monokai", line_numbers=True, word_wrap=True)
        final_new_syntax = Syntax(fixed_code, lang, theme="monokai", line_numbers=True, word_wrap=True, highlight_lines=all_changed_lines)

        final_diff_table.add_row(final_orig_syntax, final_new_syntax)
        
        console.print("\n")
        console.print(final_diff_table)

        if Confirm.ask(f"[bold white]Apply these bulk changes to {filepath}?[/bold white]"):
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed_code)
            
            stats_panel = Panel(
                f"[bold green]File Remediation Complete[/bold green]\n"
                f"[white]Target:[/white] {filepath}\n"
                f"[white]Violations Resolved:[/white] {len(violations)}\n"
                f"[white]Total Lines Added:[/white] [green]+{total_added}[/green]\n"
                f"[white]Total Lines Removed:[/white] [red]-{total_removed}[/red]",
                border_style="green"
            )
            console.print(stats_panel)
            return len(violations), total_added, total_removed
        else:
            console.print("[dim][SYSTEM] Remediation skipped.[/dim]")
            return 0, 0, 0

    except Exception as e:
        console.print(f"[bold red][ERROR] llm-remediator encountered a system error:[/bold red] {str(e)[:150]}...")
        return 0, 0, 0