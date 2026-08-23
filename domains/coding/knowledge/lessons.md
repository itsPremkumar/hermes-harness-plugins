# Knowledge — coding domain

## Lessons
- Correctness gate uses exact list-of-dict equality: key order inside each dict
  does not matter, but LIST order does (sort contract: qty desc, id asc).
- The benchmark regenerates the payload each trial; mutation of the input list
  is allowed but wasteful copies show up as lost throughput.
- Baseline is O(unique_keys * n). Any single-pass dict aggregation removes the
  inner scan entirely — historically the largest jump available here.
- dict.items() + one final sort beats building intermediate lists per key.
- EMPIRICAL SURPRISE (a005): nested-dict accumulation measured FASTER than the
  flat tuple-key dict (~7.74M vs ~6.74M rows/sec) — per-row `dict.get` on an
  int key beats hashing a fresh (id, region) tuple in CPython. Hypotheses lose
  to measurements; never assume direction.
- Wall-clock noise: re-benchmarking IDENTICAL code can swing ~1% and sneak past
  the improvement gate. Trust big deltas; treat <2% "wins" as suspect.
