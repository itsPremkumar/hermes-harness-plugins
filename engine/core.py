"""hermes-harness core: persistent memory (Lineage) + durable task state.

AVO principle: state must live OUTSIDE the LLM context window, survive
crashes, and never be rewritten destructively (append-only ledger).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path


class Lineage:
    """Append-only experiment ledger (P_t in arXiv:2603.24517 terms)."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict) -> None:
        record["ts"] = record.get("ts") or time.strftime("%Y-%m-%dT%H:%M:%S")
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # torn last line after a crash: ignore, ledger stays valid
        return out

    def tail(self, n: int = 5) -> list[dict]:
        return self.entries()[-n:]

    def best(self) -> float | None:
        scores = [e["score"] for e in self.entries()
                  if e.get("decision") == "ACCEPTED" and isinstance(e.get("score"), (int, float))]
        return max(scores) if scores else None

    def plateau(self, k: int) -> bool:
        """True when the last k attempts produced zero improvement on best."""
        ents = self.entries()
        if len(ents) < k:
            return False
        best_so_far = None
        window = []
        for e in ents:
            s = e.get("score") if e.get("decision") == "ACCEPTED" else None
            if s is not None and (best_so_far is None or s > best_so_far):
                best_so_far = s
            window.append(s if (s is not None and best_so_far == s and
                                e.get("decision") == "ACCEPTED") else 0)
        # improvement flag: 1 only when the entry raised the running best
        improved_flags = []
        best_so_far = None
        for e in ents:
            s = e.get("score") if e.get("decision") == "ACCEPTED" else None
            if s is not None and (best_so_far is None or s > best_so_far):
                improved_flags.append(1)
                best_so_far = s
            else:
                improved_flags.append(0)
        return sum(improved_flags[-k:]) == 0


class State:
    """Durable controller state — one JSON file per domain, atomic writes."""

    DEFAULT = {
        "iteration": 0,        # gate invocations so far
        "attempts": 0,         # total variation attempts recorded
        "accepted": 0,
        "best_score": None,
        "best_version": None,
        "strategy": "",
        "strategy_index": 0,
        "strategy_cycles": 0,
        "stagnation": 0,       # consecutive non-improving gated attempts
        "status": "running",
    }

    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> dict:
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            merged = dict(self.DEFAULT)
            merged.update(data)
            return merged
        return dict(self.DEFAULT)

    def save(self, state: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)  # atomic on same volume -> crash-safe checkpoint
