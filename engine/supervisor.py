"""hermes-harness supervisor: deterministic trajectory monitor.

Mirrors AVO's supervisor role: watch for stagnation / unproductive cycles
and redirect strategy. Deliberately rule-based (no LLM) in V1.
"""
from __future__ import annotations


STAGNATION_LIMIT = 3          # non-improving attempts before a redirect
MAX_STRATEGY_CYCLES = 2       # full passes through the strategy list before STOP


def decide(state: dict, strategies: list[str]) -> dict:
    if state.get("status") != "running":
        return {"action": state["status"].upper(), "reason": f"task already {state['status']}"}
    if not strategies:
        return {"action": "CONTINUE", "reason": "no strategy list configured"}
    if state.get("stagnation", 0) >= STAGNATION_LIMIT:
        nxt = (state.get("strategy_index", 0) + 1) % len(strategies)
        cycles = state.get("strategy_cycles", 0)
        if state.get("strategy_index", 0) == len(strategies) - 1:
            cycles += 1
        if cycles >= MAX_STRATEGY_CYCLES:
            return {"action": "STOP",
                    "reason": f"{state['stagnation']} stagnant attempts and all "
                              f"{len(strategies)} strategies cycled {cycles}x without progress"}
        return {"action": "ROTATE_STRATEGY",
                "to": strategies[nxt],
                "index": nxt,
                "cycles": cycles,
                "reason": f"{state['stagnation']} consecutive attempts without improvement"}
    return {"action": "CONTINUE",
            "reason": f"stagnation {state.get('stagnation', 0)}/{STAGNATION_LIMIT}"}
