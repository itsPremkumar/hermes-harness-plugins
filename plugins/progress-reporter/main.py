"""Progress reporter plugin: human status lines; sole voice for 'complete'."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "engine"))
import checklist as cl  # noqa: E402
import goal as goal_mod  # noqa: E402


def register(kr):
    kr.add_hook("post_gate", report, priority=100)   # last word


def report(ctx):
    state = ctx["state"]
    root, domain = ctx["root"], ctx["domain_arg"]
    g = goal_mod.load_goal(root, domain)
    items = cl.load(root, domain)
    done, summary = cl.verdict(items)

    lines = ["[reporter]",
             f"  goal     : {goal_mod.goal_excerpt(g)}"]
    if items:
        bar = "#" * summary["passed"] + "." * (summary["total"] - summary["passed"])
        lines.append(f"  checklist [{bar:<12}] {summary['passed']}/{summary['total']}")
        for r in summary["remaining"][:4]:
            lines.append(f"     - {r['status']:>7}: {r['item'][:60]}")
    else:
        lines.append("  checklist: (none defined)")
    lines.append(f"  progress : best={state.get('best_score')} "
                 f"attempts={state.get('attempts')} "
                 f"stagnation={state.get('stagnation')}/{3}")

    if state.get("status") == "completed" and done:
        lines.append("  VERDICT  : [COMPLETE] project finished - all "
                     "checklist items verified with recorded proof.")
    elif state.get("status") == "completed":
        lines.append("  VERDICT  : [WARN] score complete but checklist "
                       "incomplete - NOT reporting completion to the user.")
    print("\n".join(lines))
    return None
