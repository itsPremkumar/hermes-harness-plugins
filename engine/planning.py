"""Planning mode: deep-think gate for the harness.

AVO's loop is only as good as the hypotheses entering it. Planning mode
forces a deliberate, structured, FRESH plan before variation attempts and
again after every stall — the moments where shallow momentum hurts most.

A plan.md is VALID only if ALL hold:
  - exists and parses
  - required sections present: ## Goal, ## Current State,
    ## Hypotheses (>= MIN_HYPOTHESES bullets), ## Next Action
  - plan_hash recorded in state.json matches the file content
    (edited-but-not-approved plans are rejected)
"""
from __future__ import annotations

import hashlib
from pathlib import Path

MIN_HYPOTHESES = 2
REQUIRED_SECTIONS = ["## Goal", "## Current State", "## Hypotheses", "## Next Action"]


def plan_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class Plan:
    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            return None
        try:
            return self.path.read_text(encoding="utf-8")
        except Exception:
            return None

    def check(self, state: dict) -> tuple[bool, str]:
        """Gate-side check: structure AND freshness."""
        text = self.load()
        if text is None:
            return False, ("no plan found - write one with "
                           "'## Goal', '## Current State', '## Hypotheses' "
                           f"(>={MIN_HYPOTHESES} bullets), '## Next Action'")
        current = plan_hash(text)
        if state.get("plan_hash") != current:
            if not state.get("plan_hash"):
                return False, "plan exists but was never approved by a gate"
            return False, "plan changed since last approved gate - re-approve"
        problems = validate_structure(text)
        if problems:
            return False, "; ".join(problems)
        return True, "plan fresh and approved"

    def hypotheses(self, text: str) -> list[str]:
        out = []
        in_hyp = False
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("## "):
                in_hyp = s.startswith("## Hypotheses")
                continue
            if in_hyp and s.startswith("- ") and len(s) > 4:
                out.append(s[2:])
        return out


def validate_structure(text: str) -> list[str]:
    """Pure structural validation - no freshness involved. [] == valid."""
    problems = []
    missing = [s for s in REQUIRED_SECTIONS if s not in text]
    if missing:
        problems.append(f"missing required sections: {missing}")
    hyp = _hypotheses(text)
    if len(hyp) < MIN_HYPOTHESES:
        problems.append(f"needs >={MIN_HYPOTHESES} hypothesis bullets, found {len(hyp)}")
    return problems


def _hypotheses(text: str) -> list[str]:
    out = []
    in_hyp = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("## "):
            in_hyp = s.startswith("## Hypotheses")
            continue
        if in_hyp and s.startswith("- ") and len(s) > 4:
            out.append(s[2:])
    return out


def approve(plan_path: Path, state: dict, domain_name: str) -> dict:
    """Validate + approve a plan; returns the state mutation to persist."""
    p = Plan(plan_path)
    text = p.load()
    if text is None:
        return {"ok": False, "error": "no plan file at " + str(plan_path)}
    problems = validate_structure(text)
    if problems:
        return {"ok": False, "error": "; ".join(problems)}
    h = plan_hash(text)
    new_state = dict(state)
    new_state["plan_hash"] = h
    resumed = state.get("status") == "halted"
    if resumed:
        new_state["status"] = "running"
    return {
        "ok": True,
        "plan_hash": h,
        "hypotheses": _hypotheses(text),
        "resumed_from_halt": resumed,
        "note": f"plan approved for {domain_name}",
    }
