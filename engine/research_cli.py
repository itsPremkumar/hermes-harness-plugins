#!/usr/bin/env python3
"""Stamp/inspect the live-research contract for a domain.

Usage:
  python engine/research_cli.py stamp <domain> [--verify] [--min N]
  python engine/research_cli.py show <domain>

Workflow: Hermes does a REAL web search (built-in web tools), writes the
findings WITH cited URLs into domains/<x>/research/live.md, then stamps.
--verify live-resolves every cited URL before accepting the stamp.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from core import State      # noqa: E402
import webresearch as wr    # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["stamp", "show"])
    ap.add_argument("domain")
    ap.add_argument("--verify", action="store_true",
                    help="LIVE-resolve every cited URL (needs network)")
    ap.add_argument("--min", type=int, default=wr.MIN_SOURCES)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent

    if args.cmd == "show":
        text = wr.load(root, args.domain)
        print(json.dumps({
            "exists": text is not None,
            "sources": len(wr.extract_urls(text)),
            "urls": wr.extract_urls(text),
            "hash": wr.hash_text(text),
        }, indent=2))
        return 0

    res = wr.stamp(root, args.domain, live_verify=args.verify,
                   min_sources=args.min)
    if res["ok"]:
        sf = root / "domains" / args.domain / "state.json"
        state = State(sf).load()
        state["research"] = {k: v for k, v in res.items() if k != "ok"}
        State(sf).save(state)

    print(json.dumps(res, indent=2))
    return 0 if res["ok"] else 8


if __name__ == "__main__":
    sys.exit(main())
