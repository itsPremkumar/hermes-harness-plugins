"""Tests for long-hours hardening: domain locking + overnight driver."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))

import locking  # noqa: E402


class TestLocking(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="lock_t_"))
        self.dir = self.tmp / "dom"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_acquire_release_reacquire(self):
        lk = locking.acquire(self.dir)
        self.assertTrue(lk.is_file())
        locking.release(lk)
        lk2 = locking.acquire(self.dir)          # free again
        locking.release(lk2)

    def test_second_acquire_busy_raises(self):
        locking.acquire(self.dir)
        with self.assertRaises(locking.DomainBusy):
            locking.acquire(self.dir)

    def test_stale_lock_stolen_when_owner_dead(self):
        lock = self.dir / ".lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text(json.dumps({"pid": 999999999,
                                    "host": "ghost",
                                    "acquired": "2000-01-01T00:00:00"}))
        lk = locking.acquire(self.dir)           # must steal, not raise
        self.assertTrue(lk.is_file())
        info = json.loads(lk.read_text(encoding="utf-8"))
        self.assertNotEqual(info["pid"], 999999999)
        locking.release(lk)

    def test_timeout_zero_is_immediate(self):
        locking.acquire(self.dir)
        t0 = __import__("time").time()
        with self.assertRaises(locking.DomainBusy):
            locking.acquire(self.dir, timeout_s=0)
        self.assertLess(__import__("time").time() - t0, 2)


import shutil  # noqa: E402  (kept at bottom to keep top imports tidy)


class TestOvernightDriver(unittest.TestCase):
    def test_help_runs(self):
        p = subprocess.run([sys.executable, "engine/overnight.py", "--help"],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        self.assertIn("domains", p.stdout)


if __name__ == "__main__":
    unittest.main()
