# DR-Remediation Agent Skill Setup & User Guide

This directory contains the full bundle for the **DR Compliance Remediation Agent Skill** compatible with VS Code and GitHub Copilot / Open Access Agents.

## Directory Structure

```text
dr-remediation/
├── SKILL.md                  # Metadata and complete natural language prompt instructions
├── README.md                 # Setup and execution guide
├── scripts/
│   └── scan_violations.py    # AST & Regex violation scanner script
└── references/
    └── dag_rules.yaml        # Rules definition YAML file containing regex pattern rules
```

## How to Install in VS Code & GitHub Copilot

### Option A: Standard Skill Directory (Recommended)
1. Copy the `dr-remediation` folder into your project repository or home directory under:
   - Workspace level: `.github/copilot/skills/dr-remediation/`
   - User level: `~/.copilot/skills/dr-remediation/`
2. Restart or reload VS Code.

### Option B: Custom Workspace Instructions
If your environment uses `.github/copilot-instructions.md`, copy the full contents of `SKILL.md` directly into `.github/copilot-instructions.md`.

## How to Trigger the Skill in Copilot Chat
In VS Code, open the GitHub Copilot Chat panel and type:
```text
@workspace act as the DR-Remediation agent. Analyze the current branch for DR compliance violations and prepare a remediation PR.
```

The agent will automatically read `SKILL.md`, query `git diff`, run `python scripts/scan_violations.py <changed_files>`, refactor hardcodings using approved patterns, re-validate, and commit/push changes.
