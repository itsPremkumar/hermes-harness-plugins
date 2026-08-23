# ADVANCED HARNESS — CODING-FIRST MASTER PLAN (V2)

> Goal: a production-grade autonomous coding harness where every phase you named —
> research → collect → plan → do → check → verify(×N) → redo-smarter → approve →
> complete-by-checklist — exists as a PLUGIN around the invariant kernel.
> The project may be reported "COMPLETE" to the user ONLY when the user's own
> goal-checklist is fully verified.

---

## PART 1 — GAP ANALYSIS (what exists vs what your vision needs)

| Your requirement | Current state | Gap |
|---|---|---|
| Research before acting | ✅ knowledge/lessons.md + lineage tail feeds hypotheses | No forced *fresh* research step after failures |
| Plan / think | ✅ planning plugin (approved, hash-stamped) | Plan not auto-invalidated by specific failure classes |
| Do the work | ✅ worker edits candidate between gates | Coding lab is a micro-benchmark, not a real repo pipeline |
| Check the work | ✅ deterministic evaluator | Single evaluation pass |
| Verify MULTIPLE times | ❌ | No multi-round verification, no flake detection |
| Error → research again → re-plan → different approach | ⚠️ partially (stagnation→rotate→halt) | No failure TAXONOMY: compile-error vs test-fail vs flaky vs missing-permission all treated identically |
| Ask user & STORE FINAL GOAL | ❌ | No goal registry |
| Completion CHECKLIST, report complete ONLY when all pass | ⚠️ score-based `complete_at` only | No itemized, evidence-backed checklist contract |
| Special permission / key / other-agent escalation → ask user | ❌ | Harness is silent; blockers just fail |

**Verdict:** the skeleton (kernel, gates, ledger, rollback, supervision,
planning, scenarios) is right and stays. V2 adds FOUR layers as plugins:

```text
LAYER 3  HUMAN CONTRACT   goal-registry · completion-checklist · permissions · reporter
LAYER 2  DEEP VERIFICATION  multi-verify · failure-triage (routes every failure)
LAYER 1  FEATURES (exist)   planning · supervision
LAYER 0  INVARIANT KERNEL   evaluate → commit-gate → ledger → checkpoint (untouchable)
```

---

## PART 2 — THE ENHANCED LOOP (coding-first)

```text
        ┌─────────────────────── PROJECT START ───────────────────────┐
        │ goal-registry: ASK USER the final goal + success criteria    │
        │ → stored in goals/<project>.json (+GOAL.md) — immutable      │
        │   without user re-approval                                   │
        │ checklist: derive COMPLETION CHECKLIST from goal             │
        │ → checklists/<project>.json  (every item has PROOF command)  │
        └──────────────────────────┬──────────────────────────────────┘
                                   ▼
   ① RESEARCH   read knowledge/ · lineage tail · codebase · (web if allowed)
        ▼
   ② PLAN       plan.md (Goal/Current State/Hypotheses≥2/Next Action) → APPROVE
        ▼
   ③ DO         worker implements ONE hypothesis on a branch/candidate
        ▼
   ④ VERIFY ×N  multi-verify plugin runs STAGED rounds:
        ┌────────────────────────────────────────────────────────────┐
        │ R1 compile/syntax  → R2 unit tests → R3 lint+types         │
        │ → R4 security scan → R5 integration/smoke                  │
        │ FAIL at any round? rerun ONCE (flake check):               │
        │   flaky → continue · real failure → FAILURE TRIAGE         │
        └────────────────────────────────────────────────────────────┘
        ▼
   ⑤ TRIAGE     failure-triage classifies and ROUTES:
        ├─ TRANSIENT      → retry same work (no new plan needed)
        ├─ FIXABLE        → worker fix-loop ≤3, same plan, targeted notes
        ├─ STRATEGIC      → back to ① RESEARCH with failure evidence
        │                   → ② RE-PLAN (different approach MANDATORY)
        │                   → ③④⑤ again  [your "redo differently" rule]
        └─ EXTERNAL       → ⑥ PERMISSIONS
        ▼
   ⑥ PERMISSIONS  blocker needing a key / tool / another agent / risky op?
        → ASK THE USER with plain explanation + options
        → decision stored (decisions/YYYYMMDD-*.json), work resumes the
          way THE USER chose; never guessed, never silently skipped
        ▼
   ⑦ GATE        all rounds green → commit-gate: improvement-only ACCEPT,
                 else reject+rollback+stagnation++ (supervision watches:
                 rotate strategy → halt forces fresh deeper plan)
        ▼
   ⑧ CHECKLIST UPDATE  each green proof ticks its checklist item;
                 each accepted commit updates evidence hashes
        ▼
   ⑨ COMPLETE?   checklist ALL PASS?
        ├─ NO  → reporter tells user exactly WHICH items remain → loop ①
        └─ YES → ONLY NOW reporter sends "PROJECT COMPLETE" with the
                 full evidence pack (goal + checklist proofs + ledger)
```

---

## PART 3 — NEW PLUGINS (all follow the existing contract)

| plugin | type | hooks | responsibility |
|---|---|---|---|
| `goal-registry` | feature | pre_gate(read), cli:create-project | capture + store final goal from USER; inject goal excerpt into every gate ctx; immutability guard |
| `completion-checklist` | feature | post_gate(update), veto(complete-only-when-all-pass) | itemized checklist w/ proof commands; blocks `task_complete` until every item PASS; generates remaining-items report |
| `multi-verify` | feature | wraps evaluator stage list (config `verify_rounds`, `flake_rerun`) | staged rounds R1–R5; flake detection; machine-readable round report into ledger detail |
| `failure-triage` | feature | post_gate(route) | classify last failure (compile/test/flaky/security/external) → route RETRY · FIX_LOOP ≤3 · FORCE_REPLAN · ESCALATE |
| `permissions` | feature | triage escalation target | emit ASK_USER requests (reason + options) to Hermes chat; persist decisions; resume per user's choice |
| `progress-reporter` | feature | post_gate | human status lines per milestone; the ONLY voice allowed to say "complete" (and only via checklist verdict) |
| `coding-pipeline` | domain upgrade | manifest `pipeline.json` | point candidate at a REAL repo; stages map to multi-verify; branch-per-attempt via git |

Kernel addition (small, backward-compatible): allow post_gate hooks to return
`{"action":"ROUTE","route":...}` consumed by run.py — routing never touches scoring.

---

## PART 4 — DATA CONTRACTS

```text
goals/<project>.json        {goal, criteria[], constraints[], approved_by_user, ts}
checklists/<project>.json   [{id, item, proof_cmd, status: PENDING/RUNNING/PASS/FAIL,
                              evidence{run_id, exit, hash}, updated}]
decisions/*.json            {request, options, user_choice, ts}   ← audit trail
runs/<id>.json              {rounds:[{stage, cmd, exit, ms, retry_of_flake}], verdict}
```

Every artifact is append-friendly, diffable, and git-committed — same law as
lineage.jsonl: the truth lives outside the model.

---

## PART 5 — BUILD ORDER (each phase ships working)

| phase | delivers | proves |
|---|---|---|
| **P1** human contract | goal-registry + completion-checklist + reporter | a project CANNOT be declared complete until its checklist passes; user asked once, goal stored |
| **P2** deep verify | multi-verify + flake detection | a planted intermittent test is caught as FLAKY, a planted compile error routes to FIX_LOOP |
| **P3** smart redo | failure-triage routing + forced re-plan path | a strategic failure forces NEW plan before next gate (exit 4 path reused) |
| **P4** ask-human | permissions + decisions log | missing-key scenario produces a clear user question, resumes per answer |
| **P5** real coding target | coding-pipeline on a live repo (branch/attempt, PR-ready commits) | full loop drives an actual repository end-to-end |
| **P6** port siblings | research/docs-sync adopt goal+checklist contracts | same UX across every domain |

Phases are independent plugins — enable/disable per scenario as always
(`scenarios.json`: e.g. `"autonomous-night"` disables permissions-asking except CRITICAL).

---

## PART 6 — NON-NEGOTIABLE LAWS (unchanged)

1. The judge is deterministic; the worker never grades itself.
2. Improvement-only acceptance; correctness gates outrank scores.
3. Rejection rolls back; best-known state is sacred.
4. "Complete" is EARNED by checklist evidence, never claimed.
5. Blockers go to the USER with an explanation — never bypassed.
