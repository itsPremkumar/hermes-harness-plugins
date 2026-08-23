# Knowledge — docs-sync domain

## Lessons
- The evaluator is EXACT about signatures: copy the `def name(params):`
  line verbatim from target.py into the docs. Reformatting breaks matching.
- Every parameter needs a backticked mention (`like_this`) inside the symbol's
  section. Defaults shown as `param=?` still only require the bare name.
- Symbols include class methods as Class.method (e.g. Pool.acquire);
  dunder methods are deliberately excluded from required coverage.
- FABRICATION IS FATAL but partial work is fine: an attempt that documents 4/9
  symbols correctly scores 44 and gets REJECTED if it also invents one fake
  signature (correct=false beats score). Rollback restores the last accepted doc.
- Score jumps come from whole missing sections (Pool block = 4 symbols at once).
