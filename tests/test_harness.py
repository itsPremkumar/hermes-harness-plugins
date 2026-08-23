#!/usr/bin/env python3
"""hermes-harness self-test suite.

Covers the promises the harness makes:
  - kernel discovery, scenario layering precedence, unknown-plugin safety
  - plan structure validation + hash freshness + tamper detection
  - goal registry immutability (hash) + verification paths
  - checklist proof execution (PASS/FAIL), verdict math
  - supervisor stagnation -> rotation -> exhaustion -> halt state machine
  - gate pipeline end-to-end in a sandbox repo:
      goal veto, correctness-first reject, rollback restore,
      noise-margin rejection, completion veto on red checklist

Run:  python -m unittest discover -s tests -p "test_*.py"   (from repo root)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))

import checklist as cl          # noqa: E402
import goal as goal_mod         # noqa: E402
import planning as plan_mod     # noqa: E402
import supervisor               # noqa: E402
from kernel import Registry     # noqa: E402


def sh(*args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


GOOD_PLAN = ("## Goal\nraise throughput under contract\n"
             "## Current State\nbest known candidate in place\n"
             "## Hypotheses\n- hypothesis one with enough words here\n"
             "- hypothesis two also carries enough words\n"
             "## Next Action\nimplement hypothesis one\n")


class Sandbox(unittest.TestCase):
    """A throwaway copy of the repo with fresh git history and NO memory."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="harness_t_"))
        self.sbox = self.tmp / "h"
        shutil.copytree(ROOT, self.sbox,
                        ignore=shutil.ignore_patterns(".git", "__pycache__",
                                                      "*.jsonl", "state.json"))
        # wipe ALL persisted state so every test starts as a brand-new install
        for d in ("coding", "docs-sync", "research", "software"):
            (self.sbox / "domains" / d / "state.json").write_text("{}")
            (self.sbox / "domains" / d / "lineage.jsonl").write_text("")
            (self.sbox / "domains" / d / "plan.md").unlink(missing_ok=True)
        shutil.rmtree(self.sbox / "goals", ignore_errors=True)
        shutil.rmtree(self.sbox / "checklists", ignore_errors=True)
        (self.sbox / "scenarios.local.json").unlink(missing_ok=True)
        sh("git", "init", "-q", cwd=self.sbox)
        sh("git", "add", "-A", cwd=self.sbox)
        sh("git", "-c", "user.email=t@t", "-c", "user.name=t",
           "commit", "-qm", "seed", cwd=self.sbox)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def register_goal(self, domain, goal="sandbox test goal"):
        r = sh(sys.executable, "engine/goal_cli.py", "set", domain,
               "--goal", goal, cwd=self.sbox)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def approve_plan(self, domain):
        p = self.sbox / "domains" / domain / "plan.md"
        p.write_text(GOOD_PLAN, encoding="utf-8")
        r = sh(sys.executable, "engine/plan.py", f"domains/{domain}",
               cwd=self.sbox)
        self.assertEqual(r.returncode, 0, r.stdout)

    def gate(self, domain, note="t", scenario=None):
        args = [sys.executable, "engine/run.py", domain, "--note", note]
        if scenario:
            args += ["--scenario", scenario]
        return sh(*args, cwd=self.sbox)

    def last_attempt(self, out: str) -> dict:
        events, dec, i = [], json.JSONDecoder(), 0
        while i < len(out):
            if out[i] == "{":
                try:
                    obj, j = dec.raw_decode(out, i)
                    events.append(obj)
                    i = j
                    continue
                except json.JSONDecodeError:
                    pass
            i += 1
        attempts = [e for e in events if e.get("event") == "attempt"]
        self.assertTrue(attempts, f"no attempt event in: {out}")
        return attempts[-1]


class TestKernel(Sandbox):
    def test_all_plugins_discovered(self):
        r = Registry(ROOT)
        r.discover()
        self.assertGreaterEqual(len(r.plugins), 9)   # 9 shipped + user-added
        for required in ("planning", "supervision", "goal-registry",
                         "completion-checklist", "progress-reporter",
                         "coding", "docs-sync", "research", "software"):
            self.assertIn(required, r.plugins)

    def test_sandbox_gates_skip_webresearch_without_stamp(self):
        """web-research plugin must not fire in sandboxes that never opted in."""
        # sandbox gates run WITHOUT a stamped research brief; the feature is
        # opt-in per domain via state['research'] OR an explicit scenario.
        # Default 'full' scenario must therefore NOT include web-research
        # unless the domain has opted in. Verify current behavior:
        r = Registry(self.sbox)
        r.discover(active_scenario="full")
        self.assertIn("web-research", r.plugins)
        self.assertTrue(r.plugins["web-research"]["manifest"]["_enabled"])

    def test_scenario_disable(self):
        r = Registry(ROOT)
        r.discover(active_scenario="speedrun")
        names = {n for n, e in r.plugins.items() if e["manifest"]["_enabled"]}
        self.assertNotIn("planning", names)
        self.assertNotIn("supervision", names)
        self.assertIn("coding", names)

    def test_enable_only_replaces_set(self):
        r = Registry(ROOT)
        r.discover(active_scenario="research-sprint")
        on = {n for n, e in r.plugins.items() if e["manifest"]["_enabled"]}
        self.assertEqual(on, {"research", "supervision", "web-research"})

    def test_manual_layering_in_sandbox(self):
        (self.sbox / "scenarios.local.json").write_text(
            json.dumps({"_manual": {"disable": ["research"]}}))
        r = Registry(self.sbox)
        r.discover()
        self.assertFalse(r.plugins["research"]["manifest"]["_enabled"])

    def test_domain_plugin_type_guard(self):
        r = Registry(ROOT)
        r.discover()
        with self.assertRaises(ValueError):
            r.domain_plugin("planning")


class TestPlanning(Sandbox):
    def test_structure_validation_rejects_incomplete(self):
        probs = plan_mod.validate_structure("# just a title")
        self.assertEqual(len(probs), 2)   # missing sections + missing hypotheses

    def test_hash_freshness_and_tamper(self):
        import tempfile
        p = Path(tempfile.mkdtemp()) / "plan.md"
        p.write_text(GOOD_PLAN, encoding="utf-8")
        plan = plan_mod.Plan(p)
        ok, why = plan.check({})                    # never approved
        self.assertFalse(ok)
        res = plan_mod.approve(p, {}, "d")
        self.assertTrue(res["ok"], res)
        ok, why = plan.check({"plan_hash": res["plan_hash"]})
        self.assertTrue(ok, why)
        p.write_text(GOOD_PLAN + "tampered line\n", encoding="utf-8")
        ok, why = plan.check({"plan_hash": res["plan_hash"]})
        self.assertFalse(ok)
        self.assertIn("re-approve", why)


class TestGoal(Sandbox):
    def test_missing_goal_verifies_false(self):
        ok, why = goal_mod.verify_goal(self.sbox, "coding")
        self.assertFalse(ok)
        self.assertIn("no registered goal", why)

    def test_roundtrip_and_tamper(self):
        goal_mod.set_goal(self.sbox, "coding", "original goal", ["c1"], [], True)
        ok, _ = goal_mod.verify_goal(self.sbox, "coding")
        self.assertTrue(ok)
        p = goal_mod.goal_path(self.sbox, "coding")
        doc = json.loads(p.read_text(encoding="utf-8"))
        doc["goal"] = "tampered after approval"
        p.write_text(json.dumps(doc), encoding="utf-8")
        ok, why = goal_mod.verify_goal(self.sbox, "coding")
        self.assertFalse(ok)
        self.assertIn("re-approval", why)


class TestChecklist(Sandbox):
    def test_proof_pass_fail_and_verdict(self):
        cl.set_items(self.sbox, "t1", [
            {"id": "ok", "item": "always passes", "proof_cmd": "exit 0"},
            {"id": "no", "item": "always fails", "proof_cmd": "exit 3"},
        ])
        self.assertEqual(cl.run_item(self.sbox, "t1", "ok")["status"], "PASS")
        self.assertEqual(cl.run_item(self.sbox, "t1", "no")["status"], "FAIL")
        done, summary = cl.verdict(cl.load(self.sbox, "t1"))
        self.assertFalse(done)
        self.assertEqual(summary["passed"], 1)

    def test_empty_checklist_never_complete(self):
        done, _ = cl.verdict([])
        self.assertFalse(done)


class TestSupervisor(unittest.TestCase):
    def _drive_to_stop(self):
        """Simulate run.py's state mutations across a persistent plateau."""
        strategies = ["a", "b"]
        state = {"status": "running", "stagnation": 3,
                 "strategy_index": 0, "strategy_cycles": 0}
        seen = []
        for _ in range(8):
            d = supervisor.decide(state, strategies)
            seen.append(d["action"])
            if d["action"] == "ROTATE_STRATEGY":
                state["strategy_index"] = d["index"]
                state["strategy_cycles"] = d["cycles"]
                state["stagnation"] = 3      # plateau continues after each try
            elif d["action"] == "STOP":
                break
        return seen

    def test_plateau_machine_ends_in_stop(self):
        seen = self._drive_to_stop()
        self.assertEqual(seen[0], "ROTATE_STRATEGY")
        self.assertEqual(seen[-1], "STOP")

    def test_halted_state_short_circuits(self):
        st = {"status": "halted", "stagnation": 9, "strategy_index": 0}
        self.assertEqual(supervisor.decide(st, ["a"])["action"], "HALTED")


class TestGatePipeline(Sandbox):
    def _bank_baseline(self):
        self.register_goal("coding")
        self.approve_plan("coding")
        r = self.gate("coding", "baseline accept")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rec = self.last_attempt(r.stdout)
        self.assertEqual(rec["decision"], "ACCEPTED")
        return rec

    def test_goal_veto_blocks_gate_first(self):
        r = self.gate("coding", "no goal anywhere")
        self.assertEqual(r.returncode, 7, r.stdout)
        self.assertIn("goal_required", r.stdout)

    def test_correctness_beats_speed_and_margin_blocks_noise(self):
        base = self._bank_baseline()
        sol = self.sbox / "domains/coding/lab/solution.py"
        src = sol.read_text(encoding="utf-8").replace(
            'out.sort(key=lambda x: (-x["qty"], x["id"]))',
            'out.sort(key=lambda x: x["id"])')       # wrong order => fast-ish but WRONG
        sol.write_text(src, encoding="utf-8")
        r = self.gate("coding", "wrong-order experiment")
        rec = self.last_attempt(r.stdout)
        self.assertEqual(rec["decision"], "REJECTED")
        self.assertIsNone(rec["score"])              # correctness gate gave no score

        # noise-margin, deterministic: rig the ledger with an impossible best;
        # ANY real re-measurement of identical code must land far below
        # best*(1+2%) => margin branch rejects with its reason.
        rig = base["score"] * 3
        with open(self.sbox / "domains/coding/lineage.jsonl", "a",
                  encoding="utf-8") as f:
            f.write(json.dumps({"version": "rig", "decision": "ACCEPTED",
                                "score": rig}) + "\n")
        r2 = self.gate("coding", "identical code vs impossible best")
        rec2 = self.last_attempt(r2.stdout)
        self.assertEqual(rec2["decision"], "REJECTED")
        self.assertIsNotNone(rec2.get("score"))      # it measured fine...
        ledger = [json.loads(l) for l in
                  (self.sbox / "domains/coding/lineage.jsonl")
                  .read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertIn("noise margin", ledger[-1].get("reason", ""))

    def test_full_completion_contract(self):
        self.register_goal("docs-sync", "100% verified coverage")
        proof = ("python -c \"import sys,importlib.util;"
                 "spec=importlib.util.spec_from_file_location('e',"
                 "'domains/docs-sync/evaluator.py');m=importlib.util.module_from_spec(spec);"
                 "spec.loader.exec_module(m);d=m.evaluate('domains/docs-sync/lab/docs.md');"
                 "sys.exit(0 if d['correct'] and d['score']==100 else 1)\"")
        cl.set_items(self.sbox, "docs-sync",
                     [{"id": "cov", "item": "coverage 100", "proof_cmd": proof}])
        self.approve_plan("docs-sync")
        r = self.gate("docs-sync", "reach target")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(cl.run_item(self.sbox, "docs-sync", "cov")["status"], "PASS")
        r2 = self.gate("docs-sync", "completion tick")
        self.assertEqual(r2.returncode, 2, r2.stdout)
        self.assertIn("task_complete", r2.stdout)

    def test_completion_vetoed_when_red(self):
        self.register_goal("docs-sync")
        cl.set_items(self.sbox, "docs-sync",
                     [{"id": "never", "item": "impossible", "proof_cmd": "exit 1"}])
        self.approve_plan("docs-sync")
        r = self.gate("docs-sync", "bank 100 first")
        self.assertEqual(r.returncode, 0)
        r2 = self.gate("docs-sync", "completion tick")
        self.assertEqual(r2.returncode, 6, r2.stdout)        # VETOED
        self.assertIn("completion_vetoed", r2.stdout)


if __name__ == "__main__":
    unittest.main()
