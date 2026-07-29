# {{PROJECT_NAME}}

{{PROJECT_PURPOSE}}

## Tech Stack

- **Language:** {{LANGUAGE}} (e.g., Python 3.11+)
- **Dependencies:** Zero external deps for mechanism code (stdlib only)
- **Agent runtimes:** Claude Code, Kiro, Codex, Cursor, Copilot
- **Enforcement:** `governance/permission.py` — three-gate permission check (CLI mode)

## Architecture

```
├── governance/permission.py   ← Enforcement engine (deny-list → phase-gate → egress)
├── observability/audit.py     ← Append-only audit log
├── feature_list.json          ← Phase DAG (tracks workflow progression)
├── tools/mcp-allowlist.json   ← Approved tools + egress hosts
├── governance/deny-list.json  ← Hard-blocked command patterns
├── context/                   ← Domain knowledge documents
├── tests/                     ← Fixture-driven tests + E2E enforcement proof
└── demo/                      ← Scripted evaluation harness (not production path)
```

## How to Run

```bash
./init.sh                       # Verify environment, check placeholders, run tests
python3 demo/demo.py            # Run enforcement demo
python3 demo/demo.py --nogate   # Same model, no enforcement (proves harness matters)
```

## How to Verify

```bash
{{PRIMARY_VERIFICATION_COMMAND}}
python3 tests/test_fixtures.py  # Permission gate ground-truth tests
python3 tests/test_e2e.py       # Day 4 enforcement proof
./init.sh                       # Full project health check
```

## Hard Constraints

{{DENY_LIST_SUMMARY}}

- Enforcement is mechanical — `governance/permission.py` evaluates every tool call
- Three gates in order: deny-list → phase-gate → egress (fail-closed, first denial wins)
- The agent CANNOT bypass, modify, or disable the permission gate
- Phase transitions require human sign-off (agent cannot self-promote phases)
- Patterns in `governance/deny-list.json` are blocked unconditionally

## Current State

See `progress.md` for session journal and `feature_list.json` for phase status.

## Domain Context

See `context/` for domain-specific knowledge:
- {{DOMAIN_CONTEXT_LINKS}}
