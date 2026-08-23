#!/usr/bin/env python3
"""Plugin manager: inspect and toggle plugins/scenarios without editing code.

Usage:
  python engine/manage.py list                     # table of plugins
  python engine/manage.py enable  research         # manual toggle (all scenarios)
  python engine/manage.py disable planning
  python engine/manage.py reset                    # clear manual toggles
  python engine/manage.py scenario full            # set active bundle for runs
  python engine/manage.py approve domains/coding   # convenience: plan approval
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kernel import Registry  # noqa: E402


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "enable", "disable", "reset",
                                    "scenario", "approve"])
    ap.add_argument("target", nargs="?", default=None)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    local = root / "scenarios.local.json"

    if args.cmd == "reset":
        local.unlink(missing_ok=True)
        print(json.dumps({"ok": True, "note": "manual toggles cleared"}, indent=2))
        return 0

    if args.cmd == "list":
        reg = Registry(root)
        reg.discover(active_scenario=args.target)
        for row in reg.table():
            flag = "x" if row["enabled"] else " "
            print(f"[{flag}] {row['name']:<12} {row['type']:<8} v{row['version']}  "
                  f"{row['description'][:60]}")
        return 0

    data = load_json(local)
    manual = data.setdefault("_manual", {})

    if args.cmd in ("enable", "disable"):
        lst = manual.setdefault("enable" if args.cmd == "enable" else "disable", [])
        if args.target not in lst:
            lst.append(args.target)
        save_json(local, data)
        print(json.dumps({"ok": True, "action": args.cmd, "plugin": args.target}, indent=2))
        return 0

    if args.cmd == "scenario":
        save_json(root / ".active_scenario", {"active": args.target})
        print(json.dumps({"ok": True, "active_scenario": args.target}, indent=2))
        return 0

    if args.cmd == "approve":
        if not args.target:
            print(json.dumps({"ok": False, "error": "approve needs <domain>"}, indent=2))
            return 3
        import subprocess
        r = subprocess.run(
            [sys.executable, str(root / "engine" / "plan.py"), "domains/" + args.target],
            capture_output=True, text=True)
        print(r.stdout.strip())
        return r.returncode


if __name__ == "__main__":
    sys.exit(main())
