"""Planning plugin: enforces the deep-think gate via pre_gate hook."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "engine"))
from planning import Plan, plan_hash, validate_structure, REQUIRED_SECTIONS, MIN_HYPOTHESES  # noqa: E402


def register(kr):
    kr.add_hook("pre_gate", check_plan, priority=20)


def check_plan(ctx):
    state = ctx["state"]
    plan = Plan(ctx["domain_dir"] / "plan.md")
    ok, why = plan.check(state)
    if not ok:
        return {
            "action": "VETO",
            "exit_code": 4,
            "payload": {
                "event": "plan_required",
                "reason": why,
                "fix": f"python engine/plan.py {ctx['domain_arg']} "
                       f"--file {ctx['domain_dir'] / 'plan.md'}",
            },
        }
    return None
