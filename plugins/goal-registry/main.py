"""Goal-registry plugin: no gating without an intact, user-approved goal."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "engine"))
import goal as goal_mod  # noqa: E402


def register(kr):
    kr.add_hook("pre_gate", require_goal, priority=5)   # FIRST of all checks


def require_goal(ctx):
    ok, why = goal_mod.verify_goal(ctx["root"], ctx["domain_arg"])
    if not ok:
        return {
            "action": "VETO",
            "exit_code": 7,
            "payload": {
                "event": "goal_required",
                "reason": why,
                "fix": ("state the final goal to Hermes, then: "
                        "python engine/goal_cli.py set <domain> "
                        "--goal \"...\" --criterion \"...\" [--criterion \"...\"]"),
                "goal_excerpt": goal_mod.goal_excerpt(
                    goal_mod.load_goal(ctx["root"], ctx["domain_arg"])),
            },
        }
    return None
