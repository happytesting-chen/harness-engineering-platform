# Harness Engineering Platform

A reusable template for building governed AI agent projects with Claude Code and Kiro.

## What this is

- **`template/`** — The generic, domain-agnostic harness skeleton. Copy it to start any new agent project.
- **`examples/`** — Filled-in instances for specific domains (starting with `red-team-harness/` for offensive security).

## Quick start

```bash
cp -r template/ my-new-agent/
cd my-new-agent/
# Fill the {{placeholders}} in CLAUDE.md, feature_list.json, deny-list.json, mcp-allowlist.json
# Add domain knowledge docs to context/
./init.sh   # verify everything is configured
```

## Architecture

The platform separates **mechanism** (code that never changes) from **policy** (JSON/Markdown files filled per domain):

- `governance/permission.py` — three-gate enforcement (deny-list → phase-gate → egress), fail-closed
- `observability/audit.py` — append-only JSON-lines audit log
- `demo/harness.py` — optional scripted agent loop for evaluation and testing
- `.claude/settings.json` hooks — the production enforcement path in Claude Code

## Spec

Full requirements, design, and implementation tasks at `.kiro/specs/harness-engineering-platform/`.

## Status

Core mechanism complete (Tasks 1-5). Template instruction files, hooks, and Red Team example in progress.
