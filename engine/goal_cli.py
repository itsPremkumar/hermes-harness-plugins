#!/usr/bin/env python3
"""Set/inspect the user's final goal for a project domain.

Usage:
  python engine/goal_cli.py set coding --goal "..." --criterion "..." [--criterion ...] [--constraint "..."]
  python engine/goal_cli.py show coding
  python engine/goal_cli.py verify coding

NOTE: `set` must only ever be run with EXPLICIT user consent — Hermes asks
the user in chat first, then records exactly what was agreed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import goal as goal_mod  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["set", "show", "verify"])
    ap.add_argument("domain")
    ap.add_argument("--goal", default=None)
    ap.add_argument("--criterion", action="append", default=[])
    ap.add_argument("--constraint", action="append", default=[])
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent

    if args.cmd == "set":
        if not args.goal:
            print(json.dumps({"ok": False, "error": "--goal required"}, indent=2))
            return 3
        doc = goal_mod.set_goal(root, args.domain, args.goal,
                                args.criterion or ["project goal achieved"],
                                args.constraint, approved_by_user=True)
        print(json.dumps({"ok": True, "goal_hash": doc["goal_hash"],
                          "criteria": len(doc["criteria"]),
                          "note": "goal registered from USER-approved statement"},
                         indent=2))
        return 0

    if args.cmd == "show":
        g = goal_mod.load_goal(root, args.domain)
        print(json.dumps(g, indent=2) if g else
              json.dumps({"error": "no goal registered"}, indent=2))
        return 0 if g else 7

    ok, why = goal_mod.verify_goal(root, args.domain)
    print(json.dumps({"ok": ok, "reason": why}, indent=2))
    return 0 if ok else 7


if __name__ == "__main__":
    sys.exit(main())
