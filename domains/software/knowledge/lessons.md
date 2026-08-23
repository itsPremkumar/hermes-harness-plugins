# Knowledge — software domain

## Pillar map (what moves the needle)
- CRITICAL x5 (weight 3 each): tests, lint, secrets, docker, deps.
  ONE critical failure => whole attempt rejected regardless of score.
- HIGH x2 (weight 1): docs, ci. These raise score but cannot save a
  candidate failing a critical pillar.
- Max reachable without HIGH pillars = round(100*15/17) = 88.

## Lessons
- Docker pillar wants ALL of: pinned base tag (no :latest), non-root USER,
  HEALTHCHECK directive. Any one missing fails the pillar.
- requirements.txt: every line needs `name==version`. Empty file = stdlib-only
  and passes; deleting the file entirely also passes as stdlib-only.
- Docs pillar parses actual os.environ.get("X") calls via AST and demands X
  appear in README.md — rename an env var and the README must follow.
- Secrets scanner flags literal assignments to password/secret/token/api_key
  names and PEM blocks anywhere in *.py/*.yml.
