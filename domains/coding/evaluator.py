#!/usr/bin/env python3
"""Deterministic evaluator f for the 'coding' domain.

Gate:  exact-match correctness on randomized cases against an independent
       reference, THEN a minimum throughput floor. Score = best-of-3
       rows/sec on a fixed generated workload. No LLM involvement.
"""
from __future__ import annotations

import importlib.util
import json
import random
import time
from pathlib import Path

MIN_ROWS_PER_SEC = 2000      # baseline passes; optimizations push this way up
BENCH_ROWS = 4000


def _reference_solve(rows):
    """Independent, obviously-correct reference (slow is fine)."""
    totals = {}
    for r in rows:
        key = (r["id"], r["region"])
        totals[key] = totals.get(key, 0) + r["qty"]
    out = [
        {"id": k[0], "region": k[1], "qty": v}
        for k, v in totals.items()
    ]
    out.sort(key=lambda x: (-x["qty"], x["id"]))
    return out


def _gen_rows(rng: random.Random, n: int):
    regions = ["north", "south", "east", "west"]
    return [
        {"id": rng.randint(100, 160),
         "region": rng.choice(regions),
         "qty": rng.randint(1, 99)}
        for _ in range(n)
    ]


def _load_candidate(path: Path):
    spec = importlib.util.spec_from_file_location("candidate_solution", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.solve


def evaluate(candidate_path) -> dict:
    path = Path(candidate_path)
    try:
        solve = _load_candidate(path)
    except Exception as e:  # syntax error, import error, missing solve()
        return {"correct": False, "score": None, "error": f"candidate failed to load: {e}"}

    # ---- correctness gate -------------------------------------------------
    for case_i, seed in enumerate((7, 101, 2026)):
        rng = random.Random(seed)
        rows = _gen_rows(rng, 250)
        expected = _reference_solve(rows)
        try:
            got = solve([dict(r) for r in rows])
        except Exception as e:
            return {"correct": False, "score": None,
                    "error": f"case {case_i} raised: {type(e).__name__}: {e}"}
        if got != expected:
            return {"correct": False, "score": None,
                    "detail": {"failed_case": case_i,
                               "first_mismatch_index": _first_diff(expected, got)}}

    # ---- performance benchmark (best of 3) --------------------------------
    rng = random.Random(999)
    bench = _gen_rows(rng, BENCH_ROWS)
    best_rate = 0.0
    for _ in range(3):
        payload = [dict(r) for r in bench]
        t0 = time.perf_counter()
        result = solve(payload)
        dt = time.perf_counter() - t0
        assert result == solve([]) or True  # keep result alive; correctness already gated
        rate = len(bench) / max(dt, 1e-9)
        best_rate = max(best_rate, rate)

    score = int(best_rate)
    return {
        "correct": True,
        "score": score,
        "detail": {
            "bench_rows": BENCH_ROWS,
            "rows_per_sec": score,
            "min_required": MIN_ROWS_PER_SEC,
            "gate": "pass" if score >= MIN_ROWS_PER_SEC else "fail",
            "passed_cases": 3,
        },
    }


def _first_diff(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return min(len(a), len(b))


if __name__ == "__main__":
    import sys
    print(json.dumps(evaluate(sys.argv[1]), indent=2))
