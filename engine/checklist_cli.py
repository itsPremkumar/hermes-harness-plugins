#!/usr/bin/env python3
"""Manage the completion checklist for a domain.

Usage:
  python engine/checklist_cli.py set coding --id tests --item "all tests pass" --proof "python -m unittest discover -s domains/coding -s ..." ...
  python engine/checklist_cli.py show coding
  python engine/checklist_cli.py run coding ITEM_ID      # execute one proof now
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import checklist as cl  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["set", "show", "run"])
    ap.add_argument("domain")
    ap.add_argument("--id", action="append", default=[])
    ap.add_argument("--item", action="append", default=[])
    ap.add_argument("--proof", action="append", default=[])
    ap.add_argument("item_id", nargs="?", default=None)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent

    if args.cmd == "set":
        n = min(len(args.id), len(args.item))
        items = [{"id": args.id[i], "item": args.item[i],
                  "proof_cmd": args.proof[i] if i < len(args.proof) else None}
                 for i in range(n)]
        if not items:
            print(json.dumps({"ok": False,
                              "error": "--id and --item required"}, indent=2))
            return 3
        cl.set_items(root, args.domain, items)
        print(json.dumps({"ok": True, "items": len(items),
                          "note": "checklist defined; all PENDING"}, indent=2))
        return 0

    if args.cmd == "show":
        items = cl.load(root, args.domain)
        if not items:
            print(json.dumps({"error": "no checklist"}, indent=2))
            return 6
        done, summary = cl.verdict(items)
        print(json.dumps({"complete": done, **summary}, indent=2))
        return 0

    if args.cmd == "run":
        if not args.item_id:
            print(json.dumps({"ok": False, "error": "item id required"}, indent=2))
            return 3
        res = cl.run_item(root, args.domain, args.item_id)
        print(json.dumps(res, indent=2))
        return 0 if res.get("ok") else 3


if __name__ == "__main__":
    sys.exit(main())
