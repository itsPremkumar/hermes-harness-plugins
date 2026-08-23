#!/usr/bin/env python3
"""hermes-harness-plugins: gate runner over the plugin kernel.

The invariant core (evaluate -> commit gate -> lineage -> checkpoint) is
hard-wired; everything else (planning, supervision, domain selection) is a
plugin that can be enabled/disabled per scenario.

Usage:
  python engine/run.py <domain> --note "hypothesis" [--scenario NAME]

Exit codes: 0 attempt gated | 2 supervisor halt/complete | 3 config error
            4 plan required/stale | 5 vetoed by plugin
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from core import Lineage, State          # noqa: E402
from kernel import Registry              # noqa: E402


def load_evaluator(path: Path):
    spec = importlib.util.spec_from_file_location("domain_evaluator", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "evaluate"), "evaluator must define evaluate(candidate_path)"
    return mod.evaluate


def git(*args, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("domain", help="plugin name, e.g. coding")
    ap.add_argument("--note", required=True)
    ap.add_argument("--scenario", default=None,
                    help="scenario key in scenarios.json / scenarios.local.json")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent

    # ---- boot the plugin system ----------------------------------------
    reg = Registry(root)
    reg.discover(active_scenario=args.scenario)

    entry = reg.domain_plugin(args.domain)
    if entry is None or not entry["manifest"]["_enabled"]:
        print(json.dumps({"event": "domain_unavailable",
                          "plugin": args.domain,
                          "hint": "engine/manage.py list  ·  engine/manage.py enable"},
                         indent=2))
        return 3

    mf = entry["manifest"]
    domain_dir = (root / mf["domain_dir"]).resolve()
    if not domain_dir.is_dir():
        print(f"[harness] domain dir missing: {domain_dir}", file=sys.stderr)
        return 3

    strategies: list[str] = mf.get("strategies", [])
    candidate = domain_dir / mf["candidate"]
    lineage = Lineage(domain_dir / "lineage.jsonl")
    state_file = domain_dir / "state.json"
    state = State(state_file).load()

    ctx = {
        "root": root,
        "domain_arg": args.domain,
        "domain_dir": domain_dir,
        "manifest": mf,
        "strategies": strategies,
        "candidate": candidate,
        "lineage": lineage,
        "state": state,
        "save_state": lambda s: State(state_file).save(s),
        "note": args.note,
        "scenario": args.scenario,
        "registry": reg,
    }

    # ---- pre_gate hook chain (supervision prio10 -> planning prio20) ----
    veto = reg.run_hook("pre_gate", ctx)
    if veto:
        State(state_file).save(ctx["state"])
        print(json.dumps(veto.get("payload", {}), indent=2))
        return int(veto.get("exit_code", 5))

    # ---- completion target ----------------------------------------------
    target = mf.get("complete_at")
    if target is not None and state.get("best_score") == target:
        state["status"] = "completed"
        State(state_file).save(state)
        print(json.dumps({"event": "task_complete",
                          "reason": f"target score {target} achieved",
                          "best_score": target}, indent=2))
        return 2

    if not candidate.exists():
        print(f"[harness] candidate missing: {candidate}", file=sys.stderr)
        return 3

    strategy = state.get("strategy") or (
        strategies[state.get("strategy_index", 0)] if strategies else "default")

    # ---- INVARIANT CORE: evaluate ---------------------------------------
    evaluate = load_evaluator(domain_dir / mf.get("evaluator", "evaluator.py"))
    result = evaluate(candidate)

    state["iteration"] += 1
    state["attempts"] += 1
    state["strategy"] = strategy

    record = {
        "version": f"{mf['name']}-a{state['attempts']:03d}",
        "strategy": strategy,
        "note": args.note,
        "correct": bool(result.get("correct")),
        "score": result.get("score"),
        "detail": {k: v for k, v in result.items() if k not in ("correct", "score")},
    }

    best = lineage.best()
    if not record["correct"]:
        record.update(decision="REJECTED", reason="failed correctness gate")
        state["stagnation"] += 1
    elif not isinstance(record["score"], (int, float)):
        record.update(decision="REJECTED", reason="evaluator returned no numeric score")
        state["stagnation"] += 1
    elif best is None or record["score"] > best:
        imp = (record["score"] - best) if best is not None else None
        record.update(decision="ACCEPTED", previous_best=best, improvement=imp)
        state["accepted"] += 1
        state["best_score"] = record["score"]
        state["best_version"] = record["version"]
        state["stagnation"] = 0
        git("add", "-A", str(domain_dir), cwd=root)
        g = git("commit", "-m",
                f"[{record['version']}] {strategy} score={record['score']} :: {args.note}",
                cwd=root)
        record["git_commit"] = (g.stdout.strip().splitlines() or [None])[0]
    else:
        record.update(decision="REJECTED",
                      reason=f"no improvement over best={best}",
                      previous_best=best)
        state["stagnation"] += 1

    lineage.append(record)                       # ⑥ persistent memory
    State(state_file).save(state)                # ⑦ checkpoint

    print(json.dumps({
        "event": "attempt",
        "domain": mf["name"],
        "version": record["version"],
        "decision": record["decision"],
        "score": record["score"],
        "best_so_far": state["best_score"],
        "attempts": state["attempts"],
        "stagnation": state["stagnation"],
        "strategy": strategy,
    }, indent=2))

    if record["decision"] == "REJECTED":
        rel = str(Path(mf["domain_dir"]) / mf["candidate"])
        git("checkout", "--", rel, cwd=root)

    post = reg.run_hook("post_gate", ctx)
    if post:
        print(json.dumps(post.get("payload", {}), indent=2))
        return int(post.get("exit_code", 0))

    nxt_state = dict(state)
    nxt_state["plan_hash"] = None  # preview only: next tick re-checks freshness
    return 0


if __name__ == "__main__":
    sys.exit(main())
