#!/usr/bin/env python3
"""Deterministic evaluator f for the 'research' domain.

Feedback channel: CITATION VERIFICATION over the live web.
A claim = a markdown bullet line in lab/brief.md. Every claim MUST cite
at least one URL. Every cited URL is checked against the real internet
(HTTP status < 400, redirects followed, HEAD with GET fallback).

    resolution_rate = resolved_urls / cited_urls          (weight 0.7)
    diversity_ratio = min(1, distinct_domains / 4)        (weight 0.3)
    score = round(100 * (0.7 * resolution_rate + 0.3 * diversity_ratio))

Correctness gate (all must hold):
  - at least MIN_CLAIMS claims (padding with fluff is not progress)
  - EVERY cited URL resolves  -> one fabricated link = correct=false
Distinct domains counted by exact host (forums.x != x); www stripped.
No API keys. Plain urllib.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlparse

MIN_CLAIMS = 4
REQUIRED_DOMAINS = 4
URL_RE = re.compile(r"https?://[^\s)\]>\"']+", re.I)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
TIMEOUT_S = 12


def _host(url: str) -> str:
    h = urlparse(url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def _resolves(url: str) -> tuple[bool, str]:
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, headers={"User-Agent": UA}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                return True, f"HTTP {r.status} ({method})"
        except urllib.error.HTTPError as e:
            # 405 = HEAD refused; retry GET. Other codes are verdicts.
            if e.code != 405:
                return False, f"HTTP {e.code}"
            if method == "GET":
                return False, f"HTTP {e.code}"
        except Exception as e:
            if method == "GET":
                return False, f"{type(e).__name__}: {e}"
            time.sleep(0.3)  # brief pause before GET fallback
    return False, "unreachable"


def evaluate(candidate_path) -> dict:
    try:
        doc = Path(candidate_path).read_text(encoding="utf-8")
    except Exception as e:
        return {"correct": False, "score": None, "error": f"candidate unreadable: {e}"}

    # Parse markdown blocks: a "- " bullet plus its continuation lines
    # (non-empty lines that aren't new bullets or headers) form ONE claim.
    claims = []
    for line in doc.splitlines() + [""]:
        s = line.strip()
        if s.startswith("- ") and len(s) > 4:
            claims.append({"text": s[2:120], "urls": URL_RE.findall(s)})
        elif claims and s and not s.startswith(("#", "- ")):
            claims[-1]["text"] = (claims[-1]["text"] + " " + s)[:120]
            claims[-1]["urls"].extend(URL_RE.findall(s))
        elif not s:
            continue  # blank line: block boundary (claims keep accumulating by design)
    claims = [c for c in claims if c["urls"] or len(c["text"]) > 4]

    if not claims:
        return {"correct": False, "score": None, "error": "no claim bullets found"}

    uncited = [c["text"] for c in claims if not c["urls"]]
    flat_urls, seen = [], set()
    for c in claims:
        for u in c["urls"]:
            if u not in seen:
                seen.add(u)
                flat_urls.append(u)

    results, resolved = {}, 0
    for u in flat_urls:
        ok, how = _resolves(u)
        results[u] = {"ok": ok, "how": how}
        resolved += 1 if ok else 0

    total = len(flat_urls)
    rate = resolved / total if total else 0.0
    domains = {_host(u) for u in flat_urls}
    diversity = min(1.0, len(domains) / REQUIRED_DOMAINS)
    score = round(100 * (0.7 * rate + 0.3 * diversity))

    enough_claims = len(claims) >= MIN_CLAIMS
    dead = [u for u, r in results.items() if not r["ok"]]
    correct = enough_claims and not uncited and not dead and total > 0

    # Network-down guard: if EVERY url failed, say so explicitly rather
    # than silently punishing the candidate for local connectivity.
    network_down = total > 0 and resolved == 0

    return {
        "correct": correct,
        "score": score,
        "detail": {
            "claims": len(claims),
            "min_required": MIN_CLAIMS,
            "enough_claims": enough_claims,
            "uncited_claims": len(uncited),
            "urls_checked": total,
            "resolved": resolved,
            "distinct_domains": len(domains),
            "dead_urls": {u: results[u]["how"] for u in dead},
            "network_down_suspected": network_down,
        },
    }


if __name__ == "__main__":
    import sys
    print(json.dumps(evaluate(sys.argv[1]), indent=2))
