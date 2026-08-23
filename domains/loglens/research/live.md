# Live Research — LogLens roadmap (collected via real web search)

Task context: prioritize LogLens features that match how practitioners
actually analyze logs in 2025-2026.

## Findings

- Structured/JSON logging is the dominant recommendation for machine
  analysis; tools should parse JSON-lines, not just plain text.
  https://middleware.io/blog/log-formatting/

- Standard levels (DEBUG/INFO/WARNING/ERROR/CRITICAL) are settled practice;
  custom levels are discouraged for libraries — LogLens should stick to
  the standard set when classifying.
  https://docs.python.org/3/howto/logging.html

- Sensitive-field masking (tokens, passwords) is a top concern; a log TOOL
  should offer masking/redaction of obvious secrets.
  https://dasroot.net/posts/2026/01/python-logging-best-practices-development-production/

- Aggregation compatibility: outputs that pipe into jq / aggregation stacks
  are explicitly recommended; JSON output mode matters.
  https://www.carmatec.com/blog/python-logging-best-practices-complete-guide/

- Multi-module/handler setup guides confirm users need quick ways to see
  handler/config issues — a `--stats` level-breakdown directly serves this.
  https://www.toptal.com/developers/python/in-depth-python-logging
- rogue line https://example.com/x
