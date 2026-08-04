# {{PROJECT_NAME}}

{{PROJECT_PURPOSE}}

## Tech Stack

- **Language:** {{LANGUAGE}} (e.g., Python 3.11+)
- **Dependencies:** Zero external deps for mechanism code (stdlib only)
- **Agent runtimes:** Claude Code, Kiro, Codex, Cursor, Copilot
- **Enforcement:** `governance/permission.py` — three-gate permission check (CLI mode)

## Architecture

```
├── governance/                       ← ENFORCEMENT + POLICY (top-level)
│   ├── permission.py                 ← Enforcement engine (deny-list → phase-gate → egress)
│   ├── deny-list.json                ← Hard-blocked command patterns
│   └── mcp-allowlist.json            ← Approved tools + egress hosts
├── Security-kit/                     ← AI-security kit
│   ├── SECURITY.md                   ← Control reference (source-tagged)
│   ├── content_trust.py              ← Data-plane content boundary
│   └── secret_scan.py                ← Secret-block hook adapter
├── Harness-Best-Practice/            ← This file + workflow state
│   ├── AGENTS.md                     ← Identity, run/verify (this file)
│   ├── progress.md                   ← Session journal + handoff
│   ├── feature_list.json             ← Phase DAG (tracks workflow progression)
│   └── Harness-Best-Practice/observability/audit.py        ← Append-only audit log
├── tests/                            ← Fixture-driven tests + E2E + hook + content-trust proofs
└── demo/                             ← Scripted evaluation harness (not production path)
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

## Reference

- [BEST-PRACTICES.md](BEST-PRACTICES.md) — Harness engineering principles (generic)

## Domain Context

See `context/` for **project-specific** AI-development assets — product/design, AI stack
(framework + model), deployment target (on-prem/cloud), architecture, methodology, scope.
(Threat model and security controls live in `Security-kit/`.)
- {{DOMAIN_CONTEXT_LINKS}}
