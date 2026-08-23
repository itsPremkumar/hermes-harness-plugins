"""hermes-harness plugin kernel.

Everything optional lives in plugins/<name>/ with:
    manifest.json  {name, type: feature|domain, enabled, ...}
    main.py        def register(kr): kr.add_hook(HOOK, fn, priority)

Feature types hook into the gate pipeline. Domain types contribute a
complete evaluation target (evaluator, candidate, strategies, complete_at).

Effective enabled-set = manifest.enabled  overlaid by  scenarios.json[active]
overlaid by scenarios.local.json (manual toggles via engine/manage.py).

Hooks (executed in priority order):
    pre_gate(ctx)       -> None | dict(action="VETO", exit_code=N, payload={...})
    on_completion(ctx)  -> None | dict(action="VETO", exit_code=6, payload={...})
                           (runs INSTEAD of declaring task_complete)
    post_gate(ctx)      -> None
The invariant core (evaluate -> commit gate -> lineage -> checkpoint)
is NOT hookable: correctness of the judge never depends on plugins.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HOOKS = ("pre_gate", "on_completion", "post_gate")


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Registry:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.plugins: dict[str, dict] = {}      # name -> {manifest, module}
        self.hooks: dict[str, list] = {h: [] for h in HOOKS}

    # ---- discovery -----------------------------------------------------
    def discover(self, active_scenario: str | None = None) -> None:
        pdir = self.root / "plugins"
        overrides = self._scenario_overrides(active_scenario)
        for ppath in sorted(pdir.iterdir()) if pdir.exists() else []:
            mf_path = ppath / "manifest.json"
            if not mf_path.is_file():
                continue
            mf = json.loads(mf_path.read_text(encoding="utf-8"))
            name = mf.get("name") or ppath.name
            enabled = bool(mf.get("enabled", True))
            if name in overrides.get("disable", []):
                enabled = False
            if name in overrides.get("enable", []):
                enabled = True
            if "enable_only" in overrides:
                enabled = name in overrides["enable_only"]
            entry = {"manifest": {**mf, "name": name, "_enabled": enabled},
                     "dir": ppath, "module": None}
            self.plugins[name] = entry
        self._bind_hooks()

    def _scenario_overrides(self, scenario: str | None) -> dict:
        out: dict = {}
        for fname in ("scenarios.json", "scenarios.local.json"):
            f = self.root / fname
            if not f.is_file():
                continue
            data = json.loads(f.read_text(encoding="utf-8"))
            # "_manual" applies in every scenario (engine/manage.py writes it);
            # scenario-specific keys layer on top.
            chosen = {**data.get("_manual", {})}
            if scenario:
                for k, v in data.get(scenario, {}).items():
                    chosen[k] = v
            for k in ("disable", "enable", "enable_only"):
                if k in chosen:
                    out[k] = chosen[k]
        return out

    def _bind_hooks(self) -> None:
        for name, entry in self.plugins.items():
            if not entry["manifest"]["_enabled"]:
                continue
            main = entry["dir"] / "main.py"
            if not main.is_file():
                continue
            mod = _load_module(main, f"harness_plugin_{name}")
            reg = _HookCollector()
            mod.register(reg)
            entry["module"] = mod
            for hook, fn, prio in reg.collected:
                self.hooks[hook].append((prio, name, fn))
        for h in HOOKS:
            self.hooks[h].sort(key=lambda t: (t[0], t[1]))

    # ---- invocation ----------------------------------------------------
    def run_hook(self, hook: str, ctx: dict):
        """Returns first VETO dict if any plugin casts one, else None."""
        for _, pname, fn in self.hooks[hook]:
            result = fn(ctx)
            if isinstance(result, dict) and result.get("action") == "VETO":
                result.setdefault("by_plugin", pname)
                return result
        return None

    # ---- queries ---------------------------------------------------------
    def domain_plugin(self, name: str) -> dict | None:
        e = self.plugins.get(name)
        if not e:
            return None
        if e["manifest"].get("type") != "domain":
            raise ValueError(f"plugin '{name}' is not a domain plugin")
        return e

    def table(self) -> list[dict]:
        rows = []
        for name, e in sorted(self.plugins.items()):
            m = e["manifest"]
            rows.append({"name": name, "type": m.get("type", "feature"),
                         "enabled": m["_enabled"],
                         "version": m.get("version", "0.0.0"),
                         "description": m.get("description", "")})
        return rows


class _HookCollector:
    def __init__(self):
        self.collected = []

    def add_hook(self, hook: str, fn, priority: int = 50) -> None:
        if hook not in HOOKS:
            raise ValueError(f"unknown hook '{hook}' (valid: {HOOKS})")
        self.collected.append((hook, fn, priority))
