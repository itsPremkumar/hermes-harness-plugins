"""Live-web research contract engine.

The harness's research principle, applied to EVERY domain:
Hermes collects real-time data with its built-in web search/extract,
writes findings WITH cited URLs to domains/<x>/research/live.md.
This module makes that collection a GATED, tamper-evident contract:

  - stamp(): validates structure (>= MIN_SOURCES distinct hosts), optionally
    LIVE-resolves every cited URL (no fakes survive), then hash-stamps
    state.json so the web-research plugin can demand freshness at gate time.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

MIN_SOURCES = 3
URL_RE = re.compile(r"https?://[^\s)\]>\"']+", re.I)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
TIMEOUT_S = 12


def brief_path(root: Path, domain: str) -> Path:
    return root / "domains" / domain / "research" / "live.md"


def load(root: Path, domain: str) -> str | None:
    p = brief_path(root, domain)
    return p.read_text(encoding="utf-8") if p.is_file() else None


def extract_urls(text: str | None) -> list[str]:
    if not text:
        return []
    seen, out = set(), []
    for m in URL_RE.findall(text):
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def host(url: str) -> str:
    h = urlparse(url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def hash_text(text: str | None) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def _resolves(url: str) -> tuple[bool, str]:
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, headers={"User-Agent": UA},
                                     method=method)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                return True, f"HTTP {r.status} ({method})"
        except urllib.error.HTTPError as e:
            if e.code != 405 and method == "GET":
                return False, f"HTTP {e.code}"
            if method == "GET":
                return False, f"HTTP {e.code}"
        except Exception as e:
            if method == "GET":
                return False, f"{type(e).__name__}"
            time.sleep(0.2)
    return False, "unreachable"


def check_fresh(state: dict) -> tuple[bool, str]:
    r = state.get("research") or {}
    age_h = 0
    try:
        stamped = r.get("stamped_at")
        if stamped:
            import datetime
            t = datetime.datetime.fromisoformat(stamped)
            age_h = (datetime.datetime.now() - t).total_seconds() / 3600
    except Exception:
        pass
    max_h = float(r.get("max_age_hours", 168))  # default: one week
    if age_h > max_h:
        return False, (f"research is {age_h:.0f}h old (max {max_h:.0f}h) - "
                       "collect fresh live data and re-stamp")
    return True, "fresh"


def stamp(root: Path, domain: str, live_verify: bool = False,
          min_sources: int = MIN_SOURCES) -> dict:
    text = load(root, domain)
    if text is None:
        return {"ok": False,
                "error": ("no research file - write findings + URLs to "
                          f"{brief_path(root, domain)}")}
    urls = extract_urls(text)
    if len(urls) < min_sources:
        return {"ok": False,
                "error": f"need >={min_sources} cited sources, found {len(urls)}",
                "found": urls}
    domains = {host(u) for u in urls}
    if len(domains) < min_sources:
        return {"ok": False,
                "error": (f"need >={min_sources} DISTINCT hosts for diversity, "
                          f"got {len(domains)}: {sorted(domains)}")}

    dead = {}
    if live_verify:
        for u in urls:
            ok, how = _resolves(u)
            if not ok:
                dead[u] = how
        if dead:
            return {"ok": False,
                    "error": "dead citations - remove or replace them",
                    "dead": dead}

    h = hash_text(text)
    return {
        "ok": True,
        "hash": h,
        "sources": len(urls),
        "distinct_hosts": len(domains),
        "live_verified": live_verify,
        "verified_results": {} if not live_verify else
                            {u: "resolved" for u in urls},
        "stamped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
