# AI News Runtime Security Demo

Build and verify a small AI + cybersecurity news application that demonstrates deployed runtime protection for tool permission, egress, external-content trust, secrets, and auditability.

## Tech Stack

- **Language:** Python 3.11+
- **Application framework:** Strands Agents (Python)
- **Model:** Claude via Anthropic API
- **UI:** Streamlit
- **Mechanism dependencies:** keep generic harness mechanism code minimal and reusable; application dependencies belong to the project implementation
- **Development agent runtimes:** Claude Code, Kiro, Codex, Cursor, Copilot
- **Enforcement:** `governance/permission.py` plus the runtime integration path

## Architecture

```
├── governance/                       ← ENFORCEMENT + PROJECT POLICY
│   ├── permission.py                 ← Tool/phase/egress permission engine
│   ├── runtime_dispatcher.py         ← Generic runtime fallback/integration path
│   ├── deny-list.json                ← Hard-blocked command patterns
│   └── mcp-allowlist.json            ← Approved development/runtime tools + egress hosts
├── Security-kit/                     ← AI-security kit
│   ├── SECURITY.md                   ← Control reference
│   ├── content_trust.py              ← Runtime data-plane content boundary
│   └── secret_scan.py                ← Existing secret-detection primitive/hook adapter
├── Harness-Best-Practice/            ← Project workflow state
│   ├── AGENTS.md                     ← Identity, run/verify (this file)
│   ├── progress.md                   ← Session journal + handoff
│   ├── feature_list.json             ← Phase DAG
│   └── observability/
│       └── audit.py                   ← Append-only audit log
├── Context/                          ← Project-specific scope, stack, deployment
├── src/                              ← AI News application code (created during build)
├── tests/                            ← Runtime integration/E2E proofs
├── demo/                             ← Existing harness demo; not the production path
└── evaluation/                       ← Quantifies expected runtime-security outcomes
```

## How to Run

During development, follow the active phase in `Harness-Best-Practice/feature_list.json`. Once the application exists, its Streamlit launch command will be recorded here and in the README.

## How to Verify

```bash
python3 -m pytest -q
python3 evaluation/eval.py
./init.sh
```

## Hard Constraints

- Build-time Claude/Kiro enforcement remains intact; do not redesign those hooks as part of the News application.
- Four permission gates in order: protected-paths → deny-list → phase-gate → egress (fail-closed, first denial wins).
- The agent cannot bypass, modify, or disable the permission mechanism/policy.
- Phase transitions require human sign-off.
- Runtime security decisions must be made outside model reasoning on the real execution path.

## Runtime Protection Scope

The deployed application must enforce the existing harness primitives at runtime.

- Framework hooks/middleware are interception points, not the security authority.
- Reuse `governance/permission.py` for runtime tool and destination permission decisions.
- Reuse the existing secret-detection logic before outbound/write-capable tool execution.
- Reuse `Security-kit/content_trust.py` on external/untrusted tool results before they enter model context.
- Reuse the existing audit recorder for runtime security decisions.
- If Strands provides a reliable before/after tool interception path, use a thin adapter there rather than duplicating orchestration logic. `runtime_dispatcher.py` remains the generic fallback/reference path.

Runtime tool path:

```text
Strands Agent
       ↓
framework runtime interception
       ↓
project runtime-security adapter
       ↓
permission.py + secret check
       ↓
ALLOW / DENY
       ↓
actual tool handler
```

Runtime result path:

```text
actual tool result
       ↓
content_trust.py
       ↓
clean / suspicious decision
       ↓
model context (only according to runtime policy)
```

All permission, egress, secret, content-trust, and relevant execution events must be auditable.

## Runtime Evaluation Requirements

The application is not complete until the actual runtime path verifies these outcomes:

- **E01:** approved tool + approved destination → ALLOW; handler executes.
- **E02:** unapproved destination → DENY; network handler execution count = 0.
- **E03:** tool absent from allowlist → DENY; handler execution count = 0.
- **E04:** instruction-shaped malicious external content → SUSPICIOUS; unsafe onward use prevented.
- **E05:** fake test credential in outbound/write-capable tool input → BLOCK; handler execution count = 0.
- **E06:** successful run has expected allowed/executed audit traces.

## Current State

See `Harness-Best-Practice/progress.md` for session journal and `Harness-Best-Practice/feature_list.json` for phase status.

## Reference

- [BEST-PRACTICES.md](BEST-PRACTICES.md) — Harness engineering principles

## Domain Context

- [../Context/ai-stack.md](../Context/ai-stack.md) — framework, model, tools and runtime-security path
- [../Context/deployment.md](../Context/deployment.md) — deployment, secrets and egress boundary
- [../Context/target-scope.md](../Context/target-scope.md) — application scope and runtime acceptance criteria
