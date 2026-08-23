# hermes-harness — Canonical Workflow Order

## PHASE 0 · PLAN (always first — before any work, again after every stall)

```text
0.1  THINK DEEP → write <domain>/plan.md:
       ## Goal            what winning means (target/metric)
       ## Current State   best score, strategy, relevant lessons
       ## Hypotheses      >= 2 ranked directions to try
       ## Next Action     the single next move

0.2  APPROVE → python engine/plan.py <domain>
       structure validated · hash stamped into state.json
       ✗ NO gate will run without a fresh approved plan (exit 4)
```

## PHASE 1 · WORK LOOP (repeats)

```text
1.1  PICK hypothesis #1 from the approved plan
        ↓  (worker = Hermes)
1.2  EDIT the candidate (code | docs | brief | app repo)
        ↓
1.3  GATE → python engine/run.py <domain> --note "<hypothesis>"
     internal execution order (fixed):
       ① supervisor pre-check   halted? stagnant? rotate?
       ② completion check       complete_at already banked?
       ③ plan freshness check   approved? unmodified since approval?
       ④ evaluate               deterministic evaluator f(candidate)
       ⑤ commit gate            correct=false → REJECT
                                score <= best      → REJECT (+rollback)
                                score >  best      → ACCEPT (+git commit)
       ⑥ lineage append         full evidence record
       ⑦ checkpoint save        atomic state.json (crash-safe)
       ⑧ decision JSON          your signal for the next move
        ↓
1.4  READ result · UPDATE knowledge/lessons.md (wins AND failures)
        ↓
1.5  LOOP → 1.1 (next hypothesis from the SAME plan)
```

## PHASE 2 · REDIRECTS (automatic, mid-loop)

```text
stagnation reaches 3        → supervisor ROTATE_STRATEGY, reset counter
all strategies cycled 2x    → task HALTED → replan_required event
                              → go to PHASE 0 (new/deeper plan resumes it)
plan edited after approval  → gate exits 4 → re-approve in PHASE 0
```

## PHASE 3 · COMPLETION

```text
complete_at target banked   → task_complete (exit 2), gate refuses further work
new goal                    → new plan.md → PHASE 0
```

## Cross-domain build order (real products)

```text
research  FIRST    verify claims/sources before building on them
software  SECOND   enterprise gauntlet before any optimization
coding    THIRD    performance evolution on top of correctness+security
docs-sync LAST     docs matched against FINAL code signatures/env vars
```

## Exit codes

| code | meaning |
|---|---|
| 0 | attempt gated (ACCEPTED or REJECTED) |
| 2 | supervisor halted / completed |
| 3 | usage/config error |
| 4 | plan required, stale, or invalid |

## Division of labor

| Worker (Hermes) | Engine (never changes) |
|---|---|
| think plans | validate/approve plans |
| form hypotheses | judge candidates |
| edit candidates | keep ledger + checkpoints |
| learn into knowledge/ | rollback failures, supervise stalls |

The worker never grades its own homework.
