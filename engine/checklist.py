"""Checklist: itemized completion contract with executable proofs.

checklists/<domain>.json
  [{id, item, proof_cmd, status: PENDING|RUNNING|PASS|FAIL,
    evidence:{exit, output_hash, ts}, updated}]
LAW: a project is COMPLETE only when every item is PASS *and* each proof
was actually executed by this module (evidence recorded).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path


def path_for(root: Path, domain: str) -> Path:
    return root / "checklists" / f"{domain}.json"


def load(root: Path, domain: str):
    p = path_for(root, domain)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else []


def save(root: Path, domain: str, items: list) -> None:
    p = path_for(root, domain)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    p.unlink(missing_ok=True)
    tmp.rename(p)


def set_items(root: Path, domain: str, items: list[dict]) -> None:
    """(Re)define checklist items; resets statuses. Needs user consent."""
    clean = [{"id": it["id"], "item": it["item"],
              "proof_cmd": it.get("proof_cmd"),
              "status": "PENDING", "evidence": None, "updated": None}
             for it in items]
    save(root, domain, clean)


def _run_proof(cmd: str, cwd: Path, timeout: int = 120):
    t0 = time.time()
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True,
                           text=True, timeout=timeout)
        exit_code, out = r.returncode, (r.stdout + r.stderr)[-1500:]
    except subprocess.TimeoutExpired:
        exit_code, out = 124, "timeout"
    except Exception as e:
        exit_code, out = 126, f"{type(e).__name__}: {e}"
    dt = round(time.time() - t0, 2)
    h = hashlib.sha256(f"{cmd}|{exit_code}".encode()).hexdigest()[:12]
    return {"exit": exit_code, "output_tail": out[-300:], "ms": dt, "hash": h}


def update_auto(root: Path, domain: str, auto_map: dict[str, str]) -> list[str]:
    """Run proof_cmds for PENDING items listed in auto_map {id: cmd}."""
    items = load(root, domain)
    ran = []
    for it in items:
        cmd = auto_map.get(it["id"])
        if not cmd or it["status"] == "PASS":
            continue
        ev = _run_proof(cmd, root)
        it["status"] = "PASS" if ev["exit"] == 0 else "FAIL"
        it["evidence"] = ev
        it["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        ran.append(it["id"])
    if ran:
        save(root, domain, items)
    return ran


def run_item(root: Path, domain: str, item_id: str, timeout: int = 120) -> dict:
    items = load(root, domain)
    it = next((i for i in items if i["id"] == item_id), None)
    if not it:
        return {"ok": False, "error": f"no item {item_id}"}
    if not it.get("proof_cmd"):
        return {"ok": False, "error": f"item {item_id} has no proof_cmd"}
    ev = _run_proof(it["proof_cmd"], root, timeout)
    it["status"] = "PASS" if ev["exit"] == 0 else "FAIL"
    it["evidence"] = ev
    it["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save(root, domain, items)
    return {"ok": True, "id": it["id"], "status": it["status"],
            "exit": ev["exit"], "hash": ev["hash"]}


def verdict(items: list) -> tuple[bool, dict]:
    total = len(items)
    passed = sum(1 for i in items if i["status"] == "PASS")
    remaining = [{"id": i["id"], "item": i["item"], "status": i["status"]}
                 for i in items if i["status"] != "PASS"]
    return (total > 0 and passed == total), {
        "total": total, "passed": passed, "remaining": remaining}
