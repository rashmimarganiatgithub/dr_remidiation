#!/usr/bin/env python3
"""DR code remediation scanner.
 
Deterministic regex-based scan for GCP DR blockers across Python, SQL, JSON, and
shell files. Emits a Markdown report and a JSON summary. Exit codes:
 
    0  no critical findings
    1  one or more critical findings
    2  scanner error (bad args, unreadable files, etc.)
 
Standard library only. Rule IDs match .github/skills/dr_skill/references/checklist.md.
"""
from __future__ import annotations
 
import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
 
# --- Rule definitions -----------------------------------------------------
 
REGION_LITERAL = r"(?:us|eu|asia|northamerica|southamerica|australia|europe)-[a-z0-9]+\d"
ZONE_LITERAL   = REGION_LITERAL + r"-[a-f]"
 
@dataclass(frozen=True)
class Rule:
    rule_id: str
    area: str
    severity: str  # critical | major | minor
    pattern: re.Pattern
    applies_to: tuple  # file suffix globs
 
# Order matters: more specific patterns (zone) before generic (region).
RULES: list[Rule] = [
    # 1. Airflow DAGs
    Rule("DR-DAG-ZONE-01",   "Airflow DAG zone literal",     "critical",
         re.compile(rf'["\']({ZONE_LITERAL})["\']'), (".py",)),
    Rule("DR-DAG-REGION-01", "Airflow DAG region literal",   "critical",
         re.compile(rf'["\']({REGION_LITERAL})["\']'), (".py",)),
    Rule("DR-DAG-GCS-01",    "GCS gs:// literal",            "critical",
         re.compile(r'gs://[a-z0-9][a-z0-9._-]{1,220}'), (".py", ".sql", ".sh", ".json", ".yaml", ".yml")),
    Rule("DR-DAG-PROJECT-01", "Hardcoded project_id kwarg", "critical",
         re.compile(r'\bproject(?:_id)?\s*=\s*["\'][a-z][a-z0-9-]{4,}["\']'), (".py",)),
    Rule("DR-DAG-BASH-01",   "BashOperator inline gcloud/bq/gsutil",  "major",
         re.compile(r'bash_command\s*=\s*["\'].*(?:gcloud|bq|gsutil)\b.*["\']'), (".py",)),
    Rule("DR-DAG-VAR-01",    "Env-encoded Airflow Variable key or default", "minor",
         re.compile(r'Variable\.get\(\s*["\'][^"\']*(?:prod|dev|us-|eu-|asia-)[^"\']*["\']'), (".py",)),
    Rule("DR-DAG-ENV-01",    "os.getenv with hardcoded fallback",     "major",
         re.compile(r'os\.getenv\(\s*["\'][^"\']+["\']\s*,\s*["\'][^"\']+["\']\s*\)'), (".py",)),
    Rule("DR-DAG-CRUN-01",   "Cloud Run function literal URL",        "major",
         re.compile(r'https://[a-z0-9-]+-[a-z0-9]+-[a-z]{2}\.a\.run\.app'), (".py", ".json", ".yaml", ".yml", ".sh")),
    Rule("DR-DAG-SM-01",     "Secret Manager literal resource path",  "critical",
         re.compile(r'projects/[a-z][a-z0-9-]+/secrets/[A-Za-z0-9_-]+'), (".py", ".json", ".yaml", ".yml", ".sh")),
 
    # 3. SQL
    Rule("DR-SQL-FQT-01",    "Fully qualified project.dataset.table",  "major",
         re.compile(r'`[a-z][a-z0-9-]+\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+`'), (".sql",)),
    Rule("DR-SQL-REGION-01", "Region-scoped INFORMATION_SCHEMA",       "critical",
         re.compile(r'`?region-[a-z0-9-]+`?\s*\.\s*INFORMATION_SCHEMA', re.IGNORECASE), (".sql",)),
 
    # 5. Shell
    Rule("DR-SH-GCLOUD-01",  "gcloud config set literal",              "critical",
         re.compile(r'gcloud\s+config\s+set\s+(?:project|compute/region|compute/zone)\s+[^\s${"\']+'), (".sh",)),
    Rule("DR-SH-BQ-01",      "bq CLI with fixed project/location",     "major",
         re.compile(r'\bbq\b[^\n]*--(?:project_id|location)=[^\s${"\']+'), (".sh",)),
    Rule("DR-SH-GSUTIL-01",  "gsutil with static gs:// path",          "major",
         re.compile(r'\bgsutil\b[^\n]*gs://[a-z0-9][a-z0-9._-]+'), (".sh",)),
 
    # 6. KMS
    Rule("DR-KMS-PATH-01",   "KMS crypto key resource path",           "critical",
         re.compile(r'projects/[a-z0-9-]+/locations/[a-z0-9-]+/keyRings/[A-Za-z0-9_-]+/cryptoKeys/[A-Za-z0-9_-]+'),
         (".py", ".json", ".yaml", ".yml", ".sh", ".tf")),
]
 
CRITICAL = "critical"
 
@dataclass
class Finding:
    finding_id: str
    rule_id: str
    file: str
    line: int
    column: int
    severity: str
    area: str
    snippet: str
 
# --- Scanner --------------------------------------------------------------
 
COMMENT_PY  = re.compile(r'^\s*#')
COMMENT_SQL = re.compile(r'^\s*--')
COMMENT_SH  = re.compile(r'^\s*#')
 
def _is_comment(line: str, suffix: str) -> bool:
    if suffix == ".sql":
        return bool(COMMENT_SQL.match(line))
    if suffix in (".py", ".sh", ".yaml", ".yml"):
        return bool(COMMENT_PY.match(line))
    return False
 
def scan_file(path: Path, root: Path) -> list[Finding]:
    suffix = path.suffix.lower()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = path.as_posix()
    findings: list[Finding] = []
    seen: set[tuple[str, int, int, str]] = set()
    lines = text.splitlines()
    counter = {r.rule_id: 0 for r in RULES}
    for rule in RULES:
        if suffix not in rule.applies_to:
            continue
        for idx, line in enumerate(lines, start=1):
            if _is_comment(line, suffix):
                continue
            for m in rule.pattern.finditer(line):
                key = (rule.rule_id, idx, m.start(), rel)
                if key in seen:
                    continue
                seen.add(key)
                counter[rule.rule_id] += 1
                findings.append(Finding(
                    finding_id=f"{rule.rule_id}-{counter[rule.rule_id]:03d}",
                    rule_id=rule.rule_id,
                    file=rel,
                    line=idx,
                    column=m.start() + 1,
                    severity=rule.severity,
                    area=rule.area,
                    snippet=line.strip()[:200],
                ))
    return findings
 
def iter_targets(paths: Iterable[str], root: Path) -> Iterable[Path]:
    suffixes = {".py", ".sql", ".sh", ".json", ".yaml", ".yml", ".tf"}
    skip_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache"}
    for p in paths:
        target = (root / p).resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError:
            continue
        if target.is_file() and target.suffix.lower() in suffixes:
            yield target
        elif target.is_dir():
            for f in target.rglob("*"):
                if not f.is_file():
                    continue
                if any(part in skip_dirs for part in f.parts):
                    continue
                if f.suffix.lower() in suffixes:
                    yield f
 
# --- Output ---------------------------------------------------------------
 
def render_markdown(findings: list[Finding], scanned: int) -> str:
    by_sev = {"critical": 0, "major": 0, "minor": 0}
    for f in findings:
        by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
    lines = [
        "# DR Code Remediation Report",
        "",
        f"- Files scanned: **{scanned}**",
        f"- Critical: **{by_sev['critical']}**",
        f"- Major: **{by_sev['major']}**",
        f"- Minor: **{by_sev['minor']}**",
        "",
    ]
    if not findings:
        lines.append("No DR blockers found.")
        return "\n".join(lines) + "\n"
    lines += [
        "## Findings",
        "",
        "| finding_id | file | line | severity | rule | area | snippet |",
        "|---|---|---:|---|---|---|---|",
    ]
    for f in findings:
        snippet = f.snippet.replace("|", "\\|")
        lines.append(f"| `{f.finding_id}` | `{f.file}` | {f.line} | {f.severity} | `{f.rule_id}` | {f.area} | `{snippet}` |")
    lines += [
        "",
        "See `.github/skills/dr-code-remediation/references/remediation-patterns.md` for before/after examples.",
        "",
    ]
    return "\n".join(lines) + "\n"
 
# --- Main -----------------------------------------------------------------
 
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="DR code remediation scanner")
    ap.add_argument("paths", nargs="*", default=["."], help="Files or directories to scan")
    ap.add_argument("--root", default=".", help="Repository root")
    ap.add_argument("--report-md", default=None, help="Write Markdown report to this path")
    ap.add_argument("--report-json", default=None, help="Write JSON report to this path")
    ap.add_argument("--fail-on", choices=["critical", "major", "any"], default="critical",
                    help="Exit non-zero when a finding of this severity (or higher) is present")
    ap.add_argument("--changed-files-from", default=None,
                    help="Read newline-separated paths to scan from this file (used in CI)")
    args = ap.parse_args(argv)
 
    root = Path(args.root).resolve()
    paths = list(args.paths)
    if args.changed_files_from:
        try:
            extra = Path(args.changed_files_from).read_text(encoding="utf-8").splitlines()
        except OSError as e:
            print(f"error: cannot read {args.changed_files_from}: {e}", file=sys.stderr)
            return 2
        paths = [p.strip() for p in extra if p.strip()]
        if not paths:
            print("No changed files to scan; skipping.")
            if args.report_md:
                Path(args.report_md).write_text("# DR Code Remediation Report\n\nNo relevant changed files.\n", encoding="utf-8")
            if args.report_json:
                Path(args.report_json).write_text(json.dumps({"findings": [], "scanned": 0}, indent=2), encoding="utf-8")
            return 0
 
    targets = list(dict.fromkeys(iter_targets(paths, root)))
    findings: list[Finding] = []
    for t in targets:
        findings.extend(scan_file(t, root))
 
    md = render_markdown(findings, scanned=len(targets))
    if args.report_md:
        Path(args.report_md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report_md).write_text(md, encoding="utf-8")
    else:
        sys.stdout.write(md)
 
    if args.report_json:
        Path(args.report_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report_json).write_text(json.dumps(
            {"findings": [asdict(f) for f in findings], "scanned": len(targets)},
            indent=2, sort_keys=True,
        ), encoding="utf-8")
 
    order = {"critical": 3, "major": 2, "minor": 1}
    threshold = {"critical": 3, "major": 2, "any": 1}[args.fail_on]
    if any(order[f.severity] >= threshold for f in findings):
        return 1
    return 0
 
if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
 
 