#!/usr/bin/env python3
"""overnight.py — bounded long-hours driver for unattended operation.

Runs gated attempts across domains until a budget is exhausted. Designed
for cron/night shifts on a modest machine:

  - per-domain attempt budget + global wall-clock deadline
  - respects the per-domain lock (skips busy domains, never wedges)
  --plan-required keeps the full human contract ON (recommended), or
  --scenario speedrun for pure autonomous grinding
  - crash of one domain never stops the others; summary at the end

Usage:
  python engine/overnight.py --domains coding loglens --max-attempts-per-domain 6 \
      --deadline-minutes 240 --scenario no-planning
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_gate(domain: str, note: str, scenario: str | None) -> tuple[int, str]:
    cmd = [sys.executable, "engine/run.py", domain, "--note", note]
    if scenario:
        cmd += ["--scenario", scenario]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       timeout=600)
    return p.returncode, (p.stdout + p.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains", nargs="+", required=True)
    ap.add_argument("--max-attempts-per-domain", type=int, default=6)
    ap.add_argument("--deadline-minutes", type=float, default=240)
    ap.add_argument("--scenario", default=None)
    ap.add_argument("--notes", nargs="*", default=[],
                    help="optional rotating notes; default generated")
    args = ap.parse_args()

    started = time.time()
    deadline = started + args.deadline_minutes * 60
    summary: list[dict] = []

    print(json.dumps({"event": "overnight_start",
                      "domains": args.domains,
                      "max_attempts_per_domain": args.max_attempts_per_domain,
                      "deadline_minutes": args.deadline_minutes,
                      "scenario": args.scenario}, indent=2))

    for domain in args.domains:
        done_here = 0
        for i in range(1, args.max_attempts_per_domain + 1):
            if time.time() >= deadline:
                summary.append({"domain": domain, "stopped": "deadline"})
                break

            note = (args.notes[i % len(args.notes)]
                    if args.notes else
                    f"overnight tick {i} ({domain})")
            try:
                code, out = run_gate(domain, note, args.scenario)
            except subprocess.TimeoutExpired:
                summary.append({"domain": domain, "tick": i,
                                "result": "TIMEOUT"})
                continue

            verdict = {"domain": domain, "tick": i, "exit": code}
            # extract the last JSON event line-block we can find
            for marker in ("\"decision\"", "\"event\": \"supervisor\"",
                           "\"event\": \"research_required\"",
                           "\"event\": \"plan_required\"",
                           "\"event\": \"goal_required\"",
                           "\"event\": \"domain_busy\"",
                           "\"event\": \"task_complete\""):
                if marker in out:
                    verdict["signal"] = marker.split("\"")[2] if "\"" in marker else marker
                    break
            if code == 9:
                verdict["result"] = "busy-skipped"
                summary.append(verdict)
                break                      # someone else owns it; move on
            if code == 2:
                verdict["result"] = "halted-or-complete"
                summary.append(verdict)
                break                      # nothing more to do here tonight
            done_here += 1
            verdict["result"] = "gated"
            summary.append(verdict)

        else:
            summary.append({"domain": domain,
                            "stopped": f"budget {args.max_attempts_per_domain}"})
        _ = done_here

    print(json.dumps({"event": "overnight_summary",
                      "elapsed_min": round((time.time() - started) / 60, 1),
                      "results": summary}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
