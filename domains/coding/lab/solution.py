"""Candidate under evolution: aggregate sales rows.

Contract (must hold):
    solve(rows) -> list of {"id", "region", "qty"} dicts
    - one entry per distinct (id, region), quantities summed
    - sorted by qty descending, ties broken by id ascending
"""


def solve(rows):
    # v4 experiment: manual nested-dict accumulation (correct, more Python
    # bytecode per row than the flat dict — expected slightly slower).
    outer = {}
    for r in rows:
        inner = outer.get(r["id"])
        if inner is None:
            outer[r["id"]] = {r["region"]: r["qty"]}
        else:
            inner[r["region"]] = inner.get(r["region"], 0) + r["qty"]
    out = []
    for pid, regions in outer.items():
        for reg, q in regions.items():
            out.append({"id": pid, "region": reg, "qty": q})
    out.sort(key=lambda x: (-x["qty"], x["id"]))
    return out
