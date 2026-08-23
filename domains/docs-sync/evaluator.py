#!/usr/bin/env python3
"""Deterministic evaluator f for the 'docs-sync' domain.

Completely different feedback channel from 'coding': STATIC ANALYSIS.
Parses target.py with ast, extracts every public callable's signature,
then verifies the candidate docs cover each with:
  - a section header containing the symbol name
  - the exact signature string
  - at least one bullet/param line per documented parameter
Score = 100 * (documented symbols / total public symbols), integer.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

TARGET = Path(__file__).parent / "target" / "target.py"


def _public_api(tree: ast.Module) -> list[dict]:
    out = []
    for node in tree.body:                       # module-level only, by design
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                out.append(_sig(node))
        elif isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                out.append({"symbol": node.name, "signature": f"class {node.name}:",
                            "params": []})
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                            and not sub.name.startswith("_") \
                            and not _is_method_override_of_dunder(sub):
                        s = _sig(sub)
                        s["symbol"] = f"{node.name}.{sub.name}"
                        out.append(s)
    return out


def _is_method_override_of_dunder(node) -> bool:
    return node.name.startswith("__") and node.name.endswith("__")


def _sig(node) -> dict:
    a = node.args
    names = [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs]
    if a.vararg:
        names.append("*" + a.vararg.arg)
    if a.kwarg:
        names.append("**" + a.kwarg.arg)
    defaults_n = len(a.defaults)
    if defaults_n:
        names = names[:-defaults_n] + [f"{n}=?"
                                       for n in names[-defaults_n:]]
    return {"symbol": node.name,
            "signature": f"def {node.name}({', '.join(names)}):",
            "params": [n for n in names if not n.startswith('*')]}


def evaluate(candidate_path) -> dict:
    try:
        tree = ast.parse(TARGET.read_text(encoding="utf-8"))
    except Exception as e:
        return {"correct": False, "score": None, "error": f"target unreadable: {e}"}
    api = _public_api(tree)
    if not api:
        return {"correct": False, "score": None, "error": "no public API found in target"}

    try:
        doc = Path(candidate_path).read_text(encoding="utf-8")
    except Exception as e:
        return {"correct": False, "score": None, "error": f"candidate unreadable: {e}"}

    missing_sig, missing_params, covered = [], [], []
    for item in api:
        sym, sig = item["symbol"], item["signature"]
        # section header mentions the symbol
        header_ok = bool(re.search(rf"(?m)^#{{1,6}}\s.*\b{re.escape(sym)}\b", doc))
        sig_ok = sig in doc
        params_ok = True
        missing = []
        for p in item["params"]:
            p_clean = p.replace("=?", "")
            if not re.search(rf"`{re.escape(p_clean)}`", doc):
                params_ok = False
                missing.append(p)
        if header_ok and sig_ok and params_ok:
            covered.append(sym)
        else:
            if not header_ok or not sig_ok:
                missing_sig.append(sym)
            if not params_ok:
                missing_params.extend(f"{sym}:{m}" for m in missing)

    coverage = round(100 * len(covered) / len(api))
    # Correctness = no FABRICATED signatures (docs may only contain real,
    # verbatim signatures from the target) plus at least one valid section.
    known_sigs = {i["signature"] for i in api}
    fabricated = []
    for m in re.finditer(r"(?m)^\s*((?:async )?(?:def|class)\s+[A-Za-z_][\w]*\(.*\)\s*:)\s*", doc):
        if m.group(1) not in known_sigs:
            fabricated.append(m.group(1))
    valid_sections = len(covered) > 0
    correct = valid_sections and not fabricated
    return {
        "correct": correct,
        "score": coverage,
        "detail": {
            "total_symbols": len(api),
            "covered": len(covered),
            "missing_sections_or_signatures": missing_sig,
            "missing_param_docs": missing_params,
            "fabricated_signatures": fabricated,
        },
    }


if __name__ == "__main__":
    import sys
    print(json.dumps(evaluate(sys.argv[1]), indent=2))
