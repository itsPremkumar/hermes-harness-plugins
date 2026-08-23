"""Completion-checklist plugin: the veto that makes 'complete' EARNED."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "engine"))
import checklist as cl  # noqa: E402


def register(kr):
    kr.add_hook("on_completion", require_all_pass, priority=10)


def require_all_pass(ctx):
    items = cl.load(ctx["root"], ctx["domain_arg"])
    if not items:
        return {
            "action": "VETO",
            "exit_code": 6,
            "payload": {
                "event": "completion_vetoed",
                "reason": "no checklist defined - define items with "
                          "executable proofs before claiming completion",
                "fix": f"python engine/checklist_cli.py set {ctx['domain_arg']} "
                       "--id <id> --item \"<text>\" --proof \"<command>\"",
            },
        }
    done, summary = cl.verdict(items)
    if not done:
        return {
            "action": "VETO",
            "exit_code": 6,
            "payload": {
                "event": "completion_vetoed",
                "reason": (f"checklist {summary['passed']}/{summary['total']} - "
                           "a project is COMPLETE only when every item passes "
                           "its recorded proof"),
                "remaining": summary["remaining"],
                "fix": "run each failing proof: python engine/checklist_cli.py "
                       f"run {ctx['domain_arg']} <item_id>",
            },
        }
    return None
