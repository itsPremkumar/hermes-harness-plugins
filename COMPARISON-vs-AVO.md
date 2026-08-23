# hermes-harness-plugins vs NVIDIA AVO — honest positioning

Context: NVIDIA's AVO (Agentic Variation Operators, arXiv:2603.24517 +
Aug-2026 ARC-AGI-3 announcement) achieved a 100.00 RHAE public-set score by
wrapping Claude Opus 5 in an architecture of persistent memory + supervision
+ improvement-only evolution. This project implements the SAME published
principles as an open-source, zero-API-key harness.

## Same DNA

| Dimension | NVIDIA AVO | this harness |
|---|---|---|
| Core idea | Agent IS the variation operator: Vary(P_t)=Agent(P_t,K,f) replaces fixed mutations | identical: the worker agent proposes; a deterministic evaluator f judges |
| Loop | inspect-plan-modify-test-benchmark-keep/reject-repeat | hypothesize-edit-evaluate-commit-gate-lineage-checkpoint |
| Persistent memory | carries implementations/results/reasoning forward | append-only lineage.jsonl + atomic state.json + knowledge/ |
| Supervisor | redirects stagnation/loops | deterministic rules: rotate strategy at plateau, halt on exhaustion |
| Domain transfer | GPU kernels -> ARC-AGI-3, only interface swapped | 5 domains (coding, docs-sync, research, software, loglens) one engine |

## Where AVO is ahead (honest)

- Scale: 7 continuous days on DGX B200 clusters; 500+ directions explored.
- Frontier models (Claude Opus 5 / GPT-5.6 Sol); this project uses free tiers by design.
- LLM-assisted supervisor depth; ours is deliberately rule-based until P2/P3.
- Memory engineering tuned to cut repeated exploration (12% fewer actions than VISTA).
- Standardized benchmark validation (ARC-AGI-3 public set).

## Where this harness is ahead

- Open source, zero API keys, runs on modest hardware (6GB RAM laptop).
- Human contract layer: user-owned goal registry (hash-guarded), completion
  checklists with EXECUTABLE proofs, earned-completion veto (exit 6),
  permission escalation path (P4 planned).
- Plugin/scenario architecture: features swap per scenario without engine edits.
- Live-web research gate: real-time data with every cited URL HTTP-resolved
  before work proceeds (fabricated links rejected by name).
- Enterprise SDLC gauntlet domain: Docker hardening, secrets scanning,
  pinned deps, docs-vs-AST consistency, CI presence.
- Honesty enforcement: fabricated citations/signatures and hardcoded secrets
  are caught and permanently recorded in the ledger.

## The defensible claim

Architecturally faithful to AVO's published principles; operationally humble
about scale. We do NOT claim to recreate AVO or its scores - NVIDIA states
their Opus 30%->100% delta is not a controlled ablation. What we demonstrate:
the same loop machinery, transferable across domains, with governance and
honesty enforcement that published AVO material does not include.

References:
- https://developer.nvidia.com/blog/nvidia-avo-reaches-100-on-arc-agi-3-demonstrating-a-frontier-level-general-purpose-architecture-for-long-horizon-autonomous-agents/
- https://arxiv.org/abs/2603.24517
