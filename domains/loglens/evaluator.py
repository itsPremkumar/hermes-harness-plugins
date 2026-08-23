"""Evaluator for the 'loglens' domain: gates the REAL loglens repo.

Feedback channel = the project's own quality signals, executed:
  tests        unittest suite of loglens itself
  lint         ruff on the real source
  cli-smoke    actual CLI runs against a generated fixture
  packaging    README/LICENSE present, no deps declared needed

correct=true requires ALL pillars; score = weighted pillar pass-rate.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT: Path | None = None   # injected by harness via PROJECT_ROOT env


def _run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
    return p.returncode, (p.stdout + p.stderr)[-1500:]


def _check_tests(proj: Path):
    code, out = _run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                     str(proj))
    m = re.search(r"Ran (\d+) test", out)
    n = int(m.group(1)) if m else 0
    return {"pass": code == 0 and n >= 6,
            "detail": {"tests_run": n, "note": "exit 0 with >=6 tests"}}


def _check_lint(proj: Path):
    code, out = _run(["ruff", "check", "loglens.py", "tests"], str(proj))
    if code == 127:
        ok = True
        try:
            compile((proj / "loglens.py").read_text(encoding="utf-8"), "l", "exec")
        except SyntaxError:
            ok = False
        return {"pass": ok, "detail": {"tool": "py_compile fallback"}}
    return {"pass": code == 0, "detail": {"tool": "ruff", "out": out[-300:]}}


FIXTURE = "\n".join([
    "2026-08-23 09:00:00 INFO service up",
    "2026-08-23 09:00:10 ERROR upstream timeout after 30s",
    "2026-08-23 09:00:20 ERROR upstream timeout after 45s",
    "2026-08-23 09:01:00 INFO recovered",
])


def _check_cli_smoke(proj: Path):
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
        f.write(FIXTURE)
        name = f.name
    try:
        c1, o1 = _run([sys.executable, "loglens.py", "scan", name], proj)
        try:
            parsed = json.loads(o1[o1.index("{"):o1.rindex("}") + 1])
        except Exception:
            return {"pass": False, "detail": {"error": "scan output not JSON"}}
        scan_ok = (c1 == 0 and parsed.get("error_count") == 2 and
                   len(parsed.get("top_error_patterns", [])) == 1 and
                   parsed["top_error_patterns"][0]["count"] == 2)
        c2, o2 = _run([sys.executable, "loglens.py", "find", name,
                       "--q", "timeout"], proj)
        find_ok = c2 == 0 and "2 match" in o2
        return {"pass": scan_ok and find_ok,
                "detail": {"scan_ok": scan_ok, "find_ok": find_ok}}
    finally:
        Path(name).unlink(missing_ok=True)


def _check_packaging(proj: Path):
    readme = (proj / "README.md").is_file()
    license_ = (proj / "LICENSE").is_file()
    req = proj / "requirements.txt"
    zero_dep = not req.exists() or all(
        l.strip().startswith("#") or not l.strip()
        for l in req.read_text(encoding="utf-8").splitlines())
    return {"pass": readme and license_ and zero_dep,
            "detail": {"readme": readme, "license": license_,
                       "zero_dependency": zero_dep}}


PILLARS = [("tests", _check_tests, 3), ("lint", _check_lint, 3),
           ("cli-smoke", _check_cli_smoke, 4), ("packaging", _check_packaging, 2)]


def evaluate(candidate_path) -> dict:
    proj = Path(candidate_path).resolve()
    results, total, earned, failed = {}, 0, 0, []
    for name, fn, w in PILLARS:
        r = fn(proj)
        results[name] = {"pass": r["pass"], "detail": r["detail"]}
        total += w
        earned += w if r["pass"] else 0
        if not r["pass"]:
            failed.append(name)
    return {"correct": not failed, "score": round(100 * earned / total),
            "detail": {"pillars": {k: v["pass"] for k, v in results.items()},
                       "critical_failures": failed,
                       "evidence": {k: v["detail"] for k, v in results.items()}}}


if __name__ == "__main__":
    raw = sys.argv[1]
    p = Path(raw)
    if not p.is_dir():
        # direct invocation convenience: resolve relative to this domain dir
        p = Path(__file__).resolve().parent / raw
    print(json.dumps(evaluate(p), indent=2))
