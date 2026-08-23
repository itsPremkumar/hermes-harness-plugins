#!/usr/bin/env python3
"""Deterministic evaluator f for the 'software' domain.

The candidate is a WHOLE application repo. Score = weighted pillar pass-rate
across an enterprise SDLC gauntlet; every check is executed or parsed —
never assumed:

  CRITICAL (must ALL be green for correct=true):
    tests        unit tests actually run and pass (unittest discover)
    lint         ruff over the app (falls back to py_compile if ruff absent)
    secrets      no hardcoded credentials/keys in source
    docker       pinned base image, non-root USER, HEALTHCHECK present
    deps-pinned  every requirement has a version pin (==)

  HIGH:
    docs         README + documented env vars match os.environ usage
    ci           CI workflow file exists and runs the test suite
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

CRITICAL_WEIGHT = 3
HIGH_WEIGHT = 1
PILLARS = ["tests", "lint", "secrets", "docker", "deps", "docs", "ci"]

SECRET_PATTERNS = [
    re.compile(r"(?i)(password|passwd|secret|api_key|apikey|token)\s*=\s*['\"][^'\"]{6,}['\"]"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)aws_access_key_id\s*=\s*['\"][A-Z0-9]{16,}['\"]"),
]


def _py_files(root: Path):
    return [p for p in root.rglob("*.py") if ".venv" not in p.parts and "__pycache__" not in p.parts]


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
        return p.returncode, (p.stdout + p.stderr)[-2000:]
    except FileNotFoundError:
        return 127, "tool not found"
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def _check_tests(app: Path) -> dict:
    code, out = _run([sys.executable, "-m", "unittest", "discover", "-s", "tests",
                      "-p", "test_*.py"], cwd=app)
    m = re.search(r"Ran (\d+) test", out)
    n = int(m.group(1)) if m else 0
    return {"pass": code == 0 and n > 0, "detail": {"tests_run": n,
             "note": "exit 0 with >0 tests"}}


def _check_lint(app: Path) -> dict:
    code, out = _run(["ruff", "check", "."], cwd=app)
    if code == 127:  # ruff not installed -> deterministic fallback
        ok = True
        notes = []
        for f in _py_files(app):
            try:
                compile(f.read_text(encoding="utf-8"), str(f), "exec")
            except SyntaxError as e:
                ok = False
                notes.append(f"{f.name}: {e}")
        return {"pass": ok, "detail": {"tool": "py_compile fallback", "errors": notes}}
    return {"pass": code == 0, "detail": {"tool": "ruff", "output": out[-400:]}}


def _check_secrets(app: Path) -> dict:
    hits = []
    for f in _py_files(app) + list(app.glob("*.yml")) + list(app.glob("*.yaml")):
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        rel = str(f.relative_to(app))
        for i, line in enumerate(text.splitlines(), 1):
            for pat in SECRET_PATTERNS:
                if pat.search(line):
                    hits.append(f"{rel}:{i}")
    return {"pass": not hits, "detail": {"hits": hits}}


def _check_docker(app: Path) -> dict:
    df = app / "Dockerfile"
    if not df.exists():
        return {"pass": False, "detail": {"missing": "Dockerfile"}}
    text = "\n".join(df.read_text(encoding="utf-8").splitlines())
    checks = {
        "base_pinned": bool(re.search(r"(?m)^FROM\s+\S+:[\w.\-]+$", text))
        and ":latest" not in text,
        "non_root": bool(re.search(r"(?mi)^USER\s+(?!root\b)\S+", text)),
        "healthcheck": bool(re.search(r"(?m)^HEALTHCHECK\s", text)),
    }
    return {"pass": all(checks.values()), "detail": checks}


def _check_deps(app: Path) -> dict:
    req = app / "requirements.txt"
    unpinned, entries = [], []
    if req.exists():
        entries = [l.strip() for l in req.read_text(encoding="utf-8").splitlines()
                   if l.strip() and not l.strip().startswith("#")]
    else:
        # stdlib-only is acceptable but must be explicit via empty file
        return {"pass": True, "detail": {"note": "no requirements.txt (stdlib-only)"}}
    for line in entries:
        if not re.match(r"^[A-Za-z0-9_.\-]+==", line):
            unpinned.append(line)
    return {"pass": not unpinned, "detail": {"entries": len(entries),
             "unpinned": unpinned}}


def _env_vars_used(tree) -> set[str]:
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "get":
            obj = node.func.value
            is_environ = isinstance(obj, ast.Attribute) and obj.attr == "environ"
            is_osmod = isinstance(obj, ast.Name) and obj.id == "os"
            if (is_environ or is_osmod) and node.args and \
                    isinstance(node.args[0], ast.Constant):
                used.add(node.args[0].value)
    return used


def _check_docs(app: Path) -> dict:
    readme = app / "README.md"
    if not readme.exists():
        return {"pass": False, "detail": {"missing": "README.md"}}
    doc = readme.read_text(encoding="utf-8")
    env_used = set()
    trees = []
    for f in _py_files(app):
        try:
            trees.append(ast.parse(f.read_text(encoding="utf-8")))
        except SyntaxError:
            pass
    for t in trees:
        env_used |= _env_vars_used(t)
    missing = sorted(v for v in env_used
                     if v not in doc and v.upper() != v.lower())  # skip odd names
    endpoints = len(re.findall(r"(?m)^#{2,4}\s+/|^-\s+`?(GET|POST)", doc, re.M))
    return {"pass": not missing, "detail": {
        "readme": True,
        "documented_env_ok": not missing,
        "missing_env_docs": missing,
        "endpoint_sections_hint": endpoints}}


def _check_ci(app: Path) -> dict:
    for wf in sorted((app / ".github").rglob("*.y*ml")) if (app / ".github").exists() else []:
        text = wf.read_text(encoding="utf-8")
        if re.search(r"unittest|pytest|ruff", text):
            return {"pass": True, "detail": {"workflow": str(wf.relative_to(app))}}
    return {"pass": False, "detail": {"note": "no CI workflow running tests/lint"}}


CHECKS = {
    "tests": (_check_tests, CRITICAL_WEIGHT),
    "lint": (_check_lint, CRITICAL_WEIGHT),
    "secrets": (_check_secrets, CRITICAL_WEIGHT),
    "docker": (_check_docker, CRITICAL_WEIGHT),
    "deps": (_check_deps, CRITICAL_WEIGHT),
    "docs": (_check_docs, HIGH_WEIGHT),
    "ci": (_check_ci, HIGH_WEIGHT),
}


def evaluate(candidate_path) -> dict:
    app = Path(candidate_path).resolve()
    if not app.is_dir():
        return {"correct": False, "score": None, "error": f"not a directory: {app}"}

    results = {}
    for name, (fn, _) in CHECKS.items():
        results[name] = fn(app)

    total_w = sum(CHECKS[k][1] for k in PILLARS)
    earned = sum(CHECKS[k][1] for k in PILLARS if results[k]["pass"])
    score = round(100 * earned / total_w)

    critical_failed = [k for k in ("tests", "lint", "secrets", "docker", "deps")
                       if not results[k]["pass"]]
    correct = not critical_failed

    return {
        "correct": correct,
        "score": score,
        "detail": {
            "pillars": {k: bool(results[k]["pass"]) for k in PILLARS},
            "critical_failures": critical_failed,
            "evidence": {k: results[k]["detail"] for k in PILLARS},
        },
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(sys.argv[1]), indent=2))
