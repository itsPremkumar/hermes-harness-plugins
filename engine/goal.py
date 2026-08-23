"""Goal registry: store THE user's final goal for a project, immutably.

Contract:
  goals/<domain>.json  {project, goal, criteria[], constraints[],
                        approved_by_user, approved_at, goal_hash}
  goals/<domain>.GOAL.md   human-readable mirror
Immutability: any edit after approval changes goal_hash -> gate refuses
until the user re-approves (explicit re-confirm step). Never silent.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def goal_path(root: Path, domain: str) -> Path:
    return root / "goals" / f"{domain}.json"


def load_goal(root: Path, domain: str) -> dict | None:
    p = goal_path(root, domain)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def verify_goal(root: Path, domain: str) -> tuple[bool, str]:
    g = load_goal(root, domain)
    if not g:
        return False, ("no registered goal - the user must state the final "
                       "goal before work is gated")
    if not g.get("approved_by_user"):
        return False, "goal exists but was never approved by the user"
    raw = json.dumps({k: g[k] for k in ("project", "goal", "criteria",
                                        "constraints")}, sort_keys=True)
    if _hash(raw) != g.get("goal_hash"):
        return False, ("goal file changed after user approval - "
                       "re-approval required")
    return True, "goal registered and intact"


def set_goal(root: Path, domain: str, goal: str, criteria: list[str],
             constraints: list[str], approved_by_user: bool = True) -> dict:
    """Write/replace a goal. Caller MUST have explicit user consent."""
    doc = {
        "project": domain,
        "goal": goal,
        "criteria": criteria,
        "constraints": constraints,
        "approved_by_user": bool(approved_by_user),
        "approved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    raw = json.dumps({k: doc[k] for k in ("project", "goal", "criteria",
                                          "constraints")}, sort_keys=True)
    doc["goal_hash"] = _hash(raw)
    out = goal_path(root, domain)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    out.unlink(missing_ok=True)
    tmp.rename(out)

    md = out.with_suffix("").with_name(out.stem + ".GOAL.md")
    lines = [f"# FINAL GOAL — {domain}", "",
             f"**{doc['goal']}**", "", "## Success criteria (checklist source)",
             *[f"- [ ] {c}" for c in criteria], ""]
    if constraints:
        lines += ["## Constraints", *[f"- {c}" for c in constraints], ""]
    lines += [f"_Approved by user: {doc['approved_at']}_",
              f"_Hash: `{doc['goal_hash']}`_"]
    md.write_text("\n".join(lines), encoding="utf-8")
    return doc


def goal_excerpt(g: dict | None, limit: int = 240) -> str:
    if not g:
        return "(no goal registered)"
    t = g["goal"].strip()
    return t if len(t) <= limit else t[:limit - 3] + "..."
