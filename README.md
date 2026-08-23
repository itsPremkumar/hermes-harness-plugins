# hermes-harness-plugins

**Plugin edition** of hermes-harness — every feature is an optional plugin
around a small invariant kernel, so you can modify/remove/enable pieces per
scenario without touching engine code. (The original monolith lives at
`C:/one/hermes-harness`; this copy is the extensible line.)

## Structure

```text
engine/
  kernel.py    registry + hook pipeline + scenario layering
  run.py       thin host: pre_gate hooks -> INVARIANT CORE -> post_gate
  plan.py      plan approval (backed by planning plugin rules)
  core.py      Lineage ledger + atomic State checkpoints   [invariant]
  planning.py  plan parsing/validation                     [used by plugin]
  supervisor.py stagnation/rotation rules                  [used by plugin]
  manage.py    list / enable / disable / scenario / approve
plugins/
  planning/    feature  deep-think gate (pre_gate veto, exit 4)
  supervision/ feature  stagnation watch + rotation + halt (pre_gate veto)
  coding/      domain   runtime benchmark evaluator
  docs-sync/   domain   AST doc-coverage evaluator
  research/    domain   live-web citation verification
  software/    domain   enterprise SDLC gauntlet
domains/<x>/   the actual labs (evaluator, candidate, knowledge, state)
scenarios.json         named enable/disable bundles
scenarios.local.json   manual toggles (manage.py writes here)
```

## Precedence

`manifest.enabled` < `_manual` (scenarios.local.json) < active scenario bundle.
`enable_only` replaces the whole set; `enable`/`disable` adjust it.

## Scenarios included

| scenario | effect |
|---|---|
| `full` | everything on |
| `no-planning` | gates skip the plan requirement |
| `research-sprint` | only research (+supervision) |
| `prod-guard` | software+docs quality only |
| `speedrun` | raw evaluate/gate loop, no features |

Run under a scenario: `python engine/run.py coding --note "..." --scenario speedrun`

## Plugin contract

Feature plugin = folder with `manifest.json` + `main.py` exposing
`register(kr)` → `kr.add_hook("pre_gate"|"post_gate", fn, priority)`.
Return `{"action": "VETO", "exit_code": N, "payload": {...}}` to block a gate.
Domain plugin = manifest only (`type: domain`) pointing at a `domains/<x>/`
folder with `evaluator.py` + candidate + strategies. Add or remove a folder —
the kernel discovers the rest.

## The invariant loop (engine/ — write once)

```
hypothesize -> act(candidate) -> evaluate(f) -> gate -> checkpoint
                                      |
                          supervisor watches trajectory:
                          stagnation -> rotate strategy -> stop when exhausted
```

- **Persistent memory**: `lineage.jsonl` append-only ledger + `state.json`
  atomic checkpoints (crash-safe, survives restarts).
- **Commit gate**: correctness first, then improvement-only acceptance.
  Rejected candidates are rolled back from git — best-known state can never
  be lost.
- **Supervisor**: deterministic stagnation detection; rotates strategies;
  halts after cycling all strategies twice without progress.

## Domains (swappable — this is the "any kind of work" property)

A domain = a folder with `domain.json`, `evaluator.py`, a candidate file,
and `knowledge/`. Three rules: deterministic evaluator, real feedback
channel, accumulated knowledge.

| Domain | Feedback channel | Candidate | Score |
|---|---|---|---|
| `domains/coding` | runtime benchmark + exact correctness gate | `lab/solution.py` | rows/sec |
| `domains/docs-sync` | static AST analysis vs source of truth | `lab/docs.md` | % API documented |
| `domains/research` | live-web citation verification (HTTP checks, no API keys) | `lab/brief.md` | claim/source verification % |
| `domains/software` | full SDLC gauntlet: tests, lint, secrets scan, Docker hardening, pinned deps, docs-vs-AST env check, CI presence | `lab/app/` (whole repo) | weighted pillar pass-rate |

The `software` domain enforces the production bar structurally: **critical
pillars (tests/lint/secrets/docker/deps) must ALL be green for an attempt to
be accepted at any score** — quality regressions can never be banked, only
fixed.

## Usage

```bash
# 0. PLAN FIRST - deep-think before acting (planning mode):
#    write <domain>/plan.md with sections: ## Goal, ## Current State,
#    ## Hypotheses (>=2 bullets), ## Next Action, then approve it:
python engine/plan.py domains/coding          # stamps plan hash into state

# 1. one gated attempt per invocation (Hermes acts between invocations):
python engine/run.py domains/coding   --note "single-pass dict aggregation"
python engine/run.py domains/docs-sync --note "document Pool methods"
python engine/run.py domains/software --note "pin deps + harden Dockerfile"

# gates REJECT without a fresh approved plan (exit 4 = plan required/stale;
# edited-after-approval plans are detected by hash and re-approval is needed)
# exit codes: 0 attempt gated | 2 supervisor halted/completed | 3 config | 4 plan
```

## Adding a new kind of work

1. `mkdir domains/<work>` with `domain.json` (name, candidate path, strategies)
2. Write `evaluator.py`: `evaluate(candidate_path) -> {correct: bool, score: number}`
3. Seed `knowledge/lessons.md`
No engine changes. Ever.
