# HOW A SINGLE WORK ORDER FLOWS THROUGH THE HARNESS

You say one sentence in chat. This is the exact machine path.

```
YOU: "Add a --stats command to loglens"
 │
 ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 0 · INTAKE (Hermes, in chat)                               │
│  • parse WHAT you want + WHICH domain (loglens/coding/...)      │
│  • if no registered goal for that domain → ASK YOU:             │
│      "What does done look like? success criteria?"              │
│    record it: engine/goal_cli.py set <domain> --goal ...        │
│  • if checklist missing → derive items from YOUR criteria,      │
│    each with an executable proof command                        │
└───────────────────────┬─────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1 · PLAN (deep-think gate)                                 │
│  Hermes writes domains/<x>/plan.md:                             │
│    ## Goal            your work order restated                   │
│    ## Current State   best score, relevant lessons              │
│    ## Hypotheses      ≥2 ranked ways to do the work             │
│    ## Next Action     the single first move                     │
│  APPROVE → python engine/manage.py approve <x>                  │
│  (hash stamped; unapproved plan = every gate exits 4)           │
└───────────────────────┬─────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2 · DO (worker loop — repeats until done or halted)        │
│                                                                 │
│   2a. PICK hypothesis #1 from approved plan                     │
│   2b. EDIT candidate (real code/docs/repo change)               │
│   2c. GATE → python engine/run.py <x> --note "<hypothesis>"     │
│       ┌──────────────────────────────────────────────┐          │
│       │ inside the gate, fixed order:                │          │
│       │ ① goal check        (exit 7 if missing)      │          │
│       │ ② supervision       stagnation≥3? rotate     │          │
│       │ ③ plan freshness    hash match? else exit 4  │          │
│       │ ④ EVALUATE          deterministic pillars:   │          │
│       │    tests · lint · cli-smoke · packaging ...  │          │
│       │ ⑤ commit gate       correct=false → REJECT   │          │
│       │                     ≤best(+margin)→ REJECT   │          │
│       │                     better      → ACCEPT+git │          │
│       │ ⑥ lineage append    evidence forever         │          │
│       │ ⑦ checkpoint save   crash-safe state.json    │          │
│       └──────────────┬───────────────────────────────┘          │
│                      ▼                                          │
│   2d. READ verdict JSON                                         │
│       ACCEPTED → update knowledge/, next hypothesis or done     │
│       REJECTED  → git auto-rollback to last good,               │
│                   write lesson, form NEW hypothesis, re-gate    │
│   2e. REPORTER prints goal + checklist bar + progress           │
└───────────────────────┬─────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3 · REDIRECTS (automatic safety net during Step 2)         │
│  3 fails same strategy → supervisor ROTATES strategy            │
│  all strategies exhausted → HALT → "replan_required"            │
│      → back to STEP 1 with deeper thinking (resume on approve)  │
│  blocker needing key/permission → ASK YOU in chat               │
│      (P4: decision logged; nothing bypassed silently)           │
└───────────────────────┬─────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4 · COMPLETE (earned, never claimed)                       │
│  score target hit → on_completion hook runs YOUR checklist:     │
│    any FAIL/PENDING item → EXIT 6 veto, named remaining items   │
│    all PASS             → task_complete                         │
│  REPORTER verdict "[COMPLETE] ... recorded proof" → only now   │
│  does Hermes tell you the work is finished — with the evidence  │
└─────────────────────────────────────────────────────────────────┘
```

## Concrete walk-through: "Add --stats to loglens"

| step | what actually happens |
|---|---|
| intake | goal exists → skipped; checklist gets new item `--stats works on fixture` proof=`python loglens.py stats fixture.log` |
| plan | hypotheses: (1) Counter over levels+patterns, (2) streaming percentile pass |
| do | edit `loglens.py`, add tests, run gate → evaluator executes 7 tests + lint + CLI smoke on a real fixture |
| verify | all green + score improved → ACCEPTED, git commit `[loglens-aNN] feature-growth score=100 :: add --stats` |
| complete | completion hook runs checklist proofs → PASS → `[COMPLETE]` reported to you |

## What you never have to think about

rollback after failures · stagnation detection · strategy rotation ·
crash recovery · evidence ledger · plan tampering · fake "done" claims.
The harness owns those. You own the goal and the final word.
