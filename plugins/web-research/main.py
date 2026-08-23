"""Web-research plugin: no gate without fresh, cited live-web data."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "engine"))
import webresearch as wr  # noqa: E402


def register(kr):
    kr.add_hook("pre_gate", require_research, priority=30)  # after planning


def require_research(ctx):
    state = ctx["state"]
    text = wr.load(ctx["root"], ctx["domain_arg"])
    current = wr.hash_text(text)

    # OPT-IN semantics: only domains that have stamped research at least once
    # are held to the live-data contract. Fresh sandboxes / legacy domains
    # pass through untouched (the research-sprint scenario forces it instead).
    if not state.get("research"):
        return None

    stale = False
    if state["research"].get("hash") != current:
        stale = True

    if stale:
        reason = "research brief changed since stamping - re-stamp"
        return {
            "action": "VETO",
            "exit_code": 8,
            "payload": {
                "event": "research_required",
                "reason": reason,
                "how": ("1) Hermes runs a REAL web search for this task "
                        "2) write findings + cited URLs to "
                        f"{ctx['domain_dir'] / 'research' / 'live.md'} "
                        "(>=3 distinct sources) "
                        "3) python engine/research_cli.py stamp "
                        f"{ctx['domain_arg']} --verify"),
            },
        }

    ok, why = wr.check_fresh(state)
    if not ok:
        return {"action": "VETO", "exit_code": 8,
                "payload": {"event": "research_required", "reason": why}}
    return None
