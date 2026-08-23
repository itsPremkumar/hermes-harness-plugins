"""Supervision plugin: stagnation watch + strategy rotation + halt."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "engine"))
import supervisor  # noqa: E402


def register(kr):
    kr.add_hook("pre_gate", supervise, priority=10)   # runs BEFORE planning


def supervise(ctx):
    state = ctx["state"]
    strategies = ctx["strategies"]
    decision = supervisor.decide(state, strategies)

    if decision["action"] == "CONTINUE":
        return None

    if decision["action"] == "ROTATE_STRATEGY":
        state["strategy_index"] = decision["index"]
        state["strategy_cycles"] = decision["cycles"]
        state["stagnation"] = 0
        state["strategy"] = decision["to"]
        ctx["lineage"].append({"event": "SUPERVISOR_REDIRECT", **decision})
        print(json.dumps({"event": "supervisor", **decision}, indent=2))
        return None

    # STOP (fresh exhaustion) or HALTED (already halted)
    payload = {"event": "supervisor", **decision}
    print(json.dumps(payload, indent=2))
    if state.get("status") == "running":
        state["status"] = "halted"
        state["status_reason"] = decision.get("reason", "")
        ctx["save_state"](state)
    if state.get("status") == "halted":
        payload["replan_required"] = {
            "reason": "halted tasks resume only after deeper re-planning",
            "fix": f"python engine/plan.py {ctx['domain_arg']} "
                   f"--file {ctx['domain_dir'] / 'plan.md'}",
        }
        print(json.dumps(payload["replan_required"], indent=2))
    return {"action": "VETO", "exit_code": 2, "payload": payload}
