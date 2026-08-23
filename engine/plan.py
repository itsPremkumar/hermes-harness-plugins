#!/usr/bin/env python3
"""Approve a domain plan (planning-mode entry point).

Usage:
  python engine/plan.py domains/software --file domains/software/plan.md

Validates structure (sections + >=2 hypotheses), stamps the plan hash into
state.json, resumes halted tasks. The NEXT gate then verifies freshness.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from core import State  # noqa: E402
from planning import Plan, approve, plan_hash  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("domain")
    ap.add_argument("--file", default=None, help="plan path (default <domain>/plan.md)")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    domain_dir = (root / args.domain).resolve()
    plan_path = (root / args.file).resolve() if args.file else domain_dir / "plan.md"

    state_file = domain_dir / "state.json"
    state = State(state_file).load()

    result = approve(plan_path, state, args.domain)
    if result["ok"]:
        h = result.pop("plan_hash")
        state.update({"plan_hash": h})
        if result.pop("resumed_from_halt"):
            state["status"] = "running"
        State(state_file).save(state)

    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 4


if __name__ == "__main__":
    sys.exit(main())
