# Knowledge — research domain

## Lessons
- Claim = one bullet + its continuation lines up to the next blank-ish block;
  URLs may live on their own line under the bullet (parser v2 handles this).
- Pre-baseline evaluator repairs are logged here (v1 missed continuation-line
  URLs; fixed BEFORE any accept existed — never touch f after baseline).
- Correctness gate is brutal on purpose: ONE dead/fabricated link rejects the
  whole attempt even if everything else verifies (same law as fabricated docs).
- Score = 70% resolution + 30% source diversity (distinct hosts / 4).
  Same-host padding adds nothing to diversity — spread across domains.
- Distinct hosts counted literally: forums.developer.nvidia.com ≠
  developer.nvidia.com; www is stripped.
- Verified-resolving sources for the AVO topic: NVIDIA dev blog, NVIDIA forums,
  arXiv abs page, thenewstack.io, explainx.ai.
- Network-down guard: if EVERY url fails at once, suspect local connectivity
  before blaming the candidate.
