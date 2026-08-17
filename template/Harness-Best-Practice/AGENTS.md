# {{PROJECT_NAME}}

{{PROJECT_PURPOSE}}

## Tech Stack

- **Language:** {{LANGUAGE}} (e.g., Python 3.11+)
- **Dependencies:** Zero external deps for mechanism code (stdlib only)
- **Agent runtimes:** Claude Code, Kiro, Codex, Cursor, Copilot
- **Enforcement:** `governance/permission.py` — four-gate permission check (CLI mode)

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
│   └── observability/
│       └── audit.py                   ← Append-only audit log
├── tests/                            ← Fixture-driven tests + E2E + hook + content-trust proofs
├── demo/                             ← Scripted enforcement demo (gate vs --nogate; not production path)
└── evaluation/                       ← Quantifies task quality (accuracy/reproducibility/latency/cost) → SNAPSHOT.md
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
python3 evaluation/eval.py      # Quantify accuracy/reproducibility/latency/cost
./init.sh                       # Full project health check
```

## Hard Constraints

{{DENY_LIST_SUMMARY}}

*** newly added ***
- Build-time enforcement is mechanical — Claude/Kiro hooks route gated development tool calls through `governance/permission.py`
*** newly added ***
- Four gates in order: protected-paths → deny-list → phase-gate → egress (fail-closed, first denial wins)
- The agent CANNOT bypass, modify, or disable the permission gate
- Phase transitions require human sign-off (agent cannot self-promote phases)
- Patterns in `governance/deny-list.json` are blocked unconditionally

*** newly added ***
## Runtime Tool Permission

- This requirement is for the **deployed AI application's runtime**, not the Claude/Kiro build-time hook path.
- Do not add or change `PreToolUse` hooks to implement runtime protection; keep the existing build harness behavior intact.
- Runtime tool execution must use `governance/runtime_dispatcher.py` as the single tool-call path.
- `runtime_dispatcher.py` must call the existing `governance/permission.py` permission check **before** invoking the actual tool, fail closed on permission-check errors, and execute the tool only when allowed.
- The orchestrator/agent loop must call the dispatcher rather than raw tool functions. Keep this integration minimal and framework-specific only where necessary.

Runtime path:

```text
Agent / Orchestrator
        ↓
governance/runtime_dispatcher.py
        ↓
governance/permission.py
        ↓
ALLOW / DENY
        ↓
Actual Tool
```
*** newly added ***

*** newly added ***
## Runtime Content Trust

- Keep the existing `Security-kit/content_trust.py` unchanged and reuse it as the runtime data-plane primitive.
- External or untrusted tool results must be screened before they are added back to the model context.
- Use `scan_text()` for generic free-text results. Use `screen_record()` when the application has a known structured schema and can define allowed fields.
- Wire the application's screening function into the optional `result_screen` callback in `governance/runtime_dispatcher.py`.
- Do not use Claude/Kiro build-time hooks as the deployed runtime content-trust implementation.

Runtime result path:

```text
Actual Tool
        ↓
governance/runtime_dispatcher.py
        ↓
result_screen callback
        ↓
Security-kit/content_trust.py
        ↓
Agent / LLM
```
*** newly added ***

## Current State

See `Harness-Best-Practice/progress.md` for session journal and
`Harness-Best-Practice/feature_list.json` for phase status.

## Reference

- [BEST-PRACTICES.md](BEST-PRACTICES.md) — Harness engineering principles (generic)

## Domain Context

See `Context/` for **project-specific** AI-development assets — product/design, AI stack
(framework + model), deployment target (on-prem/cloud), architecture, methodology, scope.
(Threat model and security controls live in `Security-kit/`.)
- {{DOMAIN_CONTEXT_LINKS}}
