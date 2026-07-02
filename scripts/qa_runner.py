#!/usr/bin/env python3
"""Q-Mol Autonomous QA Agent — Continuous quality assurance runner.

Run this script to perform automated QA cycles on the Q-Mol app.
It tests, audits, and reports issues. Run it repeatedly for continuous QA.

Usage:
    python scripts/qa_runner.py              # Run one cycle
    python scripts/qa_runner.py --loops 5   # Run 5 cycles
    python scripts/qa_runner.py --forever   # Run until Ctrl+C

Exit codes:
    0 = All clean
    1 = Issues found
"""
from __future__ import annotations
import argparse
import ast
import json
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS_FILE = ROOT / "data" / "qa_results.jsonl"
REPORT_FILE = ROOT / "data" / "qa_report.md"
PYTHON = str(ROOT / ".venv" / "Scripts" / "python.exe")
if not Path(PYTHON).exists():
    PYTHON = sys.executable


@dataclass
class QAResult:
    cycle: int
    timestamp: str
    tests_passed: int
    tests_failed: int
    tests_skipped: int
    syntax_errors: list[str]
    unused_imports: list[str]
    smoke_test_ok: bool
    circular_imports: list[str]
    issues: list[str]
    duration_seconds: float


def _run(cmd: list[str] | str, timeout: int = 120) -> tuple[int, str, str]:
    """Run a shell command, return (exit_code, stdout, stderr)."""
    if isinstance(cmd, str):
        cmd = cmd.split()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT)
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"


def cycle_test_suite(cycle: int) -> tuple[int, int, int, list[str]]:
    """Run pytest and collect results."""
    print(f"  [Cycle {cycle}] Running test suite...")
    code, out, err = _run([PYTHON, "-m", "pytest", "tests/", "-q", "--tb=line"], timeout=300)
    
    passed = failed = skipped = 0
    issues = []
    
    for line in (out + err).splitlines():
        # Look for summary line like: "372 passed, 4 skipped, 1 warning in 194.17s"
        if "passed" in line and " in " in line and ("failed" in line or "skipped" in line or "warning" in line):
            parts = line.split(",")
            for p in parts:
                p = p.strip()
                if "passed" in p:
                    passed = int(p.split()[0])
                elif "failed" in p:
                    failed = int(p.split()[0])
                elif "skipped" in p:
                    skipped = int(p.split()[0])
        elif line.startswith("FAILED") or line.startswith("ERROR"):
            issues.append(line.strip())
    
    # Fallback: if no summary found, try alternate format
    if passed == 0 and failed == 0:
        for line in (out + err).splitlines():
            if line.startswith("==") and "passed" in line:
                import re
                m = re.search(r'(\d+) passed', line)
                if m: passed = int(m.group(1))
                m = re.search(r'(\d+) failed', line)
                if m: failed = int(m.group(1))
                m = re.search(r'(\d+) skipped', line)
                if m: skipped = int(m.group(1))
    
    if failed > 0:
        issues.append(f"{failed} test(s) failed")
    
    print(f"    -> {passed} passed, {failed} failed, {skipped} skipped")
    return passed, failed, skipped, issues


def cycle_syntax_check(cycle: int) -> list[str]:
    """Check all Python files for syntax errors."""
    print(f"  [Cycle {cycle}] Checking syntax...")
    issues = []
    for pyfile in ROOT.rglob("*.py"):
        if ".venv" in str(pyfile) or "__pycache__" in str(pyfile):
            continue
        try:
            ast.parse(pyfile.read_text(encoding="utf-8"))
        except SyntaxError as e:
            issues.append(f"Syntax error in {pyfile}: {e}")
        except UnicodeDecodeError as e:
            issues.append(f"Unicode error in {pyfile}: {e}")
    
    if issues:
        print(f"    -> {len(issues)} syntax error(s)")
    else:
        print("    -> All files compile OK")
    return issues


def cycle_smoke_test(cycle: int) -> tuple[bool, list[str]]:
    """Start server, hit endpoints, stop server."""
    print(f"  [Cycle {cycle}] Smoke testing live server...")
    issues = []
    
    # Start server
    proc = subprocess.Popen(
        [PYTHON, "-m", "uvicorn", "api:app", "--host", "127.0.0.1", "--port", "9999"],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(3)  # Wait for startup
    
    ok = True
    endpoints = [
        ("GET", "http://127.0.0.1:9999/health", None),
        ("GET", "http://127.0.0.1:9999/v1/health", None),
        ("GET", "http://127.0.0.1:9999/v1/ready", None),
        ("GET", "http://127.0.0.1:9999/v1/plans", None),
        ("POST", "http://127.0.0.1:9999/v1/compute", b'{"smiles": ["CCO"]}'),
        ("POST", "http://127.0.0.1:9999/v1/signup", b'{"email": "qa@example.com"}'),
    ]
    
    for method, url, data in endpoints:
        try:
            req = urllib.request.Request(url, data=data, method=method)
            if data:
                req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status >= 400:
                    issues.append(f"{method} {url} -> {resp.status}")
                    ok = False
        except Exception as e:
            issues.append(f"{method} {url} -> {e}")
            ok = False
    
    # Cleanup
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    
    if ok:
        print("    -> All endpoints responsive")
    else:
        print(f"    -> {len(issues)} endpoint issue(s)")
    return ok, issues


def cycle_import_check(cycle: int) -> list[str]:
    """Check for circular imports."""
    print(f"  [Cycle {cycle}] Checking imports...")
    issues = []
    modules = [
        "api", "src.db", "src.compute", "src.keys", "src.harvest",
        "src.celery_app", "src.tasks", "src.webhooks_out",
        "src.webhooks.service", "src.routers.v1",
    ]
    for mod in modules:
        code, out, err = _run([PYTHON, "-c", f"import {mod}"], timeout=15)
        if code != 0:
            issues.append(f"Import failed: {mod}: {err}")
    
    if issues:
        print(f"    -> {len(issues)} import issue(s)")
    else:
        print("    -> All imports OK")
    return issues


def cycle_unused_imports(cycle: int) -> list[str]:
    """Find unused imports (only report, don't fail)."""
    print(f"  [Cycle {cycle}] Checking for unused imports...")
    issues = []
    for pyfile in (ROOT / "src").rglob("*.py"):
        try:
            tree = ast.parse(pyfile.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        
        imports = {}
        names_used = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports[alias.asname or alias.name] = (pyfile, alias.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    if name != "*":
                        imports[name] = (pyfile, f"{node.module}.{alias.name}")
            elif isinstance(node, ast.Name):
                names_used.add(node.id)
        
        for name, (f, orig) in imports.items():
            if name not in names_used and not name.startswith("_") and name not in ("annotations",):
                # Skip common false positives
                if "annotations" in str(orig) or name in ("List", "Dict", "Optional", "Any", "Tuple"):
                    continue
                # Skip __init__.py re-exports
                if f.name == "__init__.py":
                    continue
                issues.append(f"{f}: {name}")
    
    print(f"    -> {len(issues)} potentially unused imports (informational only)")
    return issues


def run_cycle(cycle: int) -> QAResult:
    """Run one complete QA cycle."""
    print(f"\n{'='*60}")
    print(f"  Q-Mol QA Cycle #{cycle}")
    print(f"  {datetime.now().isoformat()}")
    print(f"{'='*60}")
    
    start = time.time()
    all_issues = []
    
    # 1. Syntax check
    syntax_errors = cycle_syntax_check(cycle)
    all_issues.extend(syntax_errors)
    
    # 2. Import check
    import_issues = cycle_import_check(cycle)
    all_issues.extend(import_issues)
    
    # 3. Test suite
    passed, failed, skipped, test_issues = cycle_test_suite(cycle)
    all_issues.extend(test_issues)
    
    # 4. Smoke test
    smoke_ok, smoke_issues = cycle_smoke_test(cycle)
    all_issues.extend(smoke_issues)
    
    # 5. Unused imports (informational)
    unused = cycle_unused_imports(cycle)
    
    duration = time.time() - start
    
    result = QAResult(
        cycle=cycle,
        timestamp=datetime.now().isoformat(),
        tests_passed=passed,
        tests_failed=failed,
        tests_skipped=skipped,
        syntax_errors=syntax_errors,
        unused_imports=unused,
        smoke_test_ok=smoke_ok,
        circular_imports=import_issues,
        issues=all_issues,
        duration_seconds=round(duration, 2),
    )
    
    # Save results
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_FILE.open("a") as f:
        f.write(json.dumps(asdict(result)) + "\n")
    
    return result


def generate_report(results: list[QAResult]) -> str:
    """Generate a Markdown report from all results."""
    lines = [
        "# Q-Mol QA Report",
        f"Generated: {datetime.now().isoformat()}",
        f"Total cycles: {len(results)}",
        "",
        "## Summary",
        "",
        "| Cycle | Timestamp | Tests | Failed | Skipped | Smoke | Issues | Duration |",
        "|-------|-----------|-------|--------|---------|-------|--------|----------|",
    ]
    
    for r in results:
        lines.append(
            f"| {r.cycle} | {r.timestamp[:19]} | {r.tests_passed}P | {r.tests_failed}F | "
            f"{r.tests_skipped}S | {'OK' if r.smoke_test_ok else 'FAIL'} | "
            f"{len(r.issues)} | {r.duration_seconds}s |"
        )
    
    # Latest issues
    if results:
        latest = results[-1]
        lines.extend(["", "## Latest Issues", ""])
        if latest.issues:
            for issue in latest.issues:
                lines.append(f"- {issue}")
        else:
            lines.append("No issues found in latest cycle.")
        
        if latest.syntax_errors:
            lines.extend(["", "### Syntax Errors", ""])
            for e in latest.syntax_errors:
                lines.append(f"- {e}")
        
        if latest.circular_imports:
            lines.extend(["", "### Circular Imports", ""])
            for e in latest.circular_imports:
                lines.append(f"- {e}")
    
    lines.extend(["", "---", "*Run `python scripts/qa_runner.py` to update this report.*"])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Q-Mol Autonomous QA Runner")
    parser.add_argument("--loops", type=int, default=1, help="Number of QA cycles to run")
    parser.add_argument("--forever", action="store_true", help="Run until interrupted")
    parser.add_argument("--delay", type=int, default=10, help="Seconds between cycles")
    args = parser.parse_args()
    
    results = []
    cycle = 0
    
    try:
        while True:
            cycle += 1
            result = run_cycle(cycle)
            results.append(result)
            
            # Generate report after each cycle
            report = generate_report(results)
            REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
            REPORT_FILE.write_text(report, encoding="utf-8")
            
            print(f"\n  Cycle {cycle} complete in {result.duration_seconds}s")
            print(f"  Report saved to: {REPORT_FILE}")
            print(f"  Results saved to: {RESULTS_FILE}")
            
            if not args.forever and cycle >= args.loops:
                break
            
            if args.forever or cycle < args.loops:
                print(f"  Waiting {args.delay}s before next cycle...")
                time.sleep(args.delay)
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    
    # Final summary
    print(f"\n{'='*60}")
    print("  QA RUN COMPLETE")
    print(f"  Total cycles: {cycle}")
    print(f"  Report: {REPORT_FILE}")
    
    if results and results[-1].issues:
        print(f"  Latest issues: {len(results[-1].issues)}")
        for issue in results[-1].issues[:5]:
            print(f"    - {issue}")
        sys.exit(1)
    else:
        print("  All clean! No issues detected.")
        sys.exit(0)


if __name__ == "__main__":
    main()
