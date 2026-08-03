# Harness Engineering Platform — Template

A reusable, zero-dependency framework for building governed AI agent projects. Copy this directory to start a new agent project with mechanical enforcement controls built in.

## Quick Start

```bash
cp -r template/ my-new-agent/
cd my-new-agent/
# Fill {{placeholders}} in: CLAUDE.md, feature_list.json, deny-list.json, mcp-allowlist.json
# Add at least one domain doc to context/
chmod +x init.sh
./init.sh
```

## What You Must Fill vs What Ships Ready

### Must Fill (project won't function without these)

| File | What to fill | Why |
|------|-------------|-----|
| `CLAUDE.md` | `{{PROJECT_NAME}}`, `{{PROJECT_PURPOSE}}`, `{{PRIMARY_VERIFICATION_COMMAND}}` | Claude Code reads this — defines session workflow and working rules |
| `AGENTS.md` | `{{PROJECT_NAME}}`, `{{PROJECT_PURPOSE}}`, `{{LANGUAGE}}`, `{{PRIMARY_VERIFICATION_COMMAND}}` | Open standard — defines what this system is, how to run/verify it (Codex, Copilot, Cursor, Gemini) |
| `feature_list.json` | Phase names, descriptions, verification commands | Phase-gate denies all tools if phases are undefined |
| `governance/deny-list.json` | Review defaults, add domain-specific patterns | Catastrophic patterns ship pre-filled; add domain rules |
| `tools/mcp-allowlist.json` | Add your domain tools, set `gated_until` where needed | Phase-gate denies tools not in this list |
| `context/` (at least one doc) | Methodology, scope, standards for your domain | Agent has no domain knowledge without this |

### Ships Ready (functional out of the box)

| File | What it does | When to modify |
|------|-------------|----------------|
| `governance/permission.py` | Three-gate enforcement engine | **Never** — mechanism, not policy |
| `observability/audit.py` | Append-only JSON-lines logging | **Never** |
| `demo/` | Scripted enforcement demo + test harness | **Never** (extend via tool handlers only) |
| `tests/` | Data-driven test runner + E2E enforcement proof | Extend `fixtures.json` with domain cases |
| `.claude/settings.json` | 5 pre-configured hooks | Extend with domain hooks, don't modify base set |
| `.claude/commands/session-cycle.md` | Generic session workflow | Works as-is; add domain commands alongside |
| `.kiro/steering/session-cycle.md` | Same for Kiro | Works as-is |
| `init.sh` | Startup verification | Works as-is |
| `progress.md` | Session continuity journal | Update every session (structure pre-filled) |

## Agent Development Lifecycle Coverage

The template maps to the full Customise → Operationalise → Secure cycle:

| Lifecycle Stage | Template Component | What it provides |
|----------------|-------------------|-----------------|
| **1. Customise** | `CLAUDE.md`, `feature_list.json`, `deny-list.json`, `mcp-allowlist.json`, `context/` | Domain expert fills placeholders — configures what the agent does, what's blocked, what's gated |
| **2. Operationalise** | `session-cycle.md`, `progress.md`, `init.sh`, `.claude/settings.json` hooks | Agent runs sessions: startup → verify → work → record → clean exit |
| **3. Secure** | `governance/permission.py`, `tests/fixtures.json`, `tests/test_e2e.py`, `demo/demo.py --nogate` | Enforcement is mechanical, tested, and provably effective |
| **4. Iterate** | Phase transitions (human sign-off), deny-list updates, fixture extensions | Harness gets stronger each session through policy refinement |

## Architecture

```
template/
├── CLAUDE.md                 ← Claude Code instruction file
├── AGENTS.md                 ← Open standard (Codex, Copilot, Cursor, Gemini, etc.)
├── feature_list.json         ← Phase DAG (domain expert fills)
├── progress.md               ← Session journal + handoff
├── init.sh                   ← Startup verification
│
├── governance/               ← ENFORCEMENT
│   ├── permission.py         ← [MECHANISM] 3-gate: deny-list → phase-gate → egress
│   └── deny-list.json        ← [POLICY] hard-blocked patterns
│
├── tools/
│   └── mcp-allowlist.json    ← [POLICY] approved tools + egress hosts
│
├── observability/
│   └── audit.py              ← [MECHANISM] append-only audit log
│
├── context/                  ← [POLICY] domain knowledge documents
│   └── README.md
│
├── tests/
│   ├── fixtures.json         ← Ground-truth test cases
│   ├── test_fixtures.py      ← Data-driven test runner
│   └── test_e2e.py           ← Day 4 enforcement proof
│
├── demo/                     ← EVALUATION (not production path)
│   ├── harness.py            ← Agent loop for demo + tests
│   ├── demo.py               ← Scripted enforcement demo
│   └── fake_model.py         ← Zero-dependency LLM mock
│
├── security/                ← SECURITY KIT (navigation + review evidence)
│   ├── README.md
│   └── control-matrix.md     ← Control → code → test → evidence (fill per project)
│
├── context/
│   ├── SECURITY.md           ← 40-control reference (source-tagged)
│   └── BEST-PRACTICES.md
│
├── .claude/                 ← CLAUDE CODE (active runtime)
│   ├── settings.json         ← Hooks: governance-check → secret-block → audit-capture
│   ├── commands/
│   │   ├── session-cycle.md  ← /session-cycle workflow
│   │   └── domain-workflow.md← Domain-specific placeholder
│   └── rules/                ← (optional) always-on rules, CLAUDE.md priority
│
└── kiro/                    ← KIRO ADD-ON (opt-in; copy to .kiro/ to activate)
    ├── README.md             ← How to activate for Kiro
    ├── hooks/                ← governance / secret-block / audit / clean-state
    └── steering/             ← session-cycle, domain-workflow, security, security-review

Note: `governance/permission.py` also gains `secret_scan.py`; `observability/` gains
`audit_hook.py`; `tests/` gains `test_hooks.py` (hook-integration proof). Every
module carries an `ARCHITECTURE.md`.
```

**Claude-native root:** everything in the active root is read by Claude Code. Kiro
support is opt-in under `kiro/` — nothing inert sits in the root. `CLAUDE.md` imports
`@AGENTS.md` so the open-standard identity file loads in Claude too.

## How Enforcement Works

**Production path:** `.claude/settings.json` hooks → `governance/permission.py` (CLI mode)

Three gates, evaluated in order (fail-closed — first denial wins):
1. **Deny-list** — Substring match against `deny-list.json` patterns → immediate block
2. **Phase-gate** — Tool must be in `mcp-allowlist.json` AND referenced phase must be "passing"
3. **Egress** — Network commands require target host in `egress_hosts` list

Exit code 0 = allow, exit code 2 = BLOCK.

## Human-in-the-Loop Points

The human doesn't approve every action — they intervene at three defined points:

1. **Phase sign-off** — Agent claims phase complete → human reviews → edits `feature_list.json` status to "passing"
2. **Escalation** — Agent is stuck → human writes decision to `progress.md`
3. **Policy update** — Audit review reveals gap → human adds pattern to deny-list or allowlist

Everything else is autonomous within the gates.

## Security Kit

The Security Kit is the template's cross-cutting security operating model. It is not a separate agent or a single prompt: it combines repository context, Kiro guidance, policy, enforcement, verification, and review evidence. It applies an approved project design; it does not make architecture decisions for the project.

### Seven Layers

| Layer | Purpose | Primary format |
|-------|---------|----------------|
| **Context** | Explain the approved security posture, threats, and controls | `context/SECURITY.md` plus project and module docs |
| **Guidance** | Shape everyday coding behaviour | `.kiro/steering/security.md` |
| **Workflow** | Review security-sensitive changes consistently | `.kiro/steering/security-review.md` |
| **Policy** | Declare permitted tools, actions, egress, and approvals | Allowlist, deny-list, feature state, approval policy |
| **Enforcement** | Prevent prohibited actions when integrated into an execution path | Policy gate, tool wrapper, runtime authorization |
| **Verification** | Demonstrate that controls work and resist known attacks | Fixtures, E2E tests, scanners, adversarial cases |
| **Lifecycle evidence** | Record decisions, approvals, findings, and residual risk | Control matrix, phase evidence, review records, Git/CI history |

### Development and Review Flow

1. The coding agent follows concise, always-on Kiro security guidance.
2. For a sensitive change—such as a tool, external API, identity, retrieval, policy, or deployment change—it manually uses the security-review workflow, reads the relevant controls, and runs mapped checks.
3. The review records findings, evidence, and unresolved risk in the control matrix and project state.
4. A human approves high-risk policy, release, or runtime-action decisions; the decision and evidence are recorded with the work.

Hooks are the activation mechanism, not the Security Kit itself: Kiro hooks provide early local feedback; Git hooks provide developer feedback; CI/CD supplies shared merge and release gates; runtime authorization is the final control for deployed agent actions.

### Security Kit v0.1

| Status | Components |
|--------|------------|
| **Included now** | [`security/README.md`](security/README.md); [`security/control-matrix.md`](security/control-matrix.md); source-tagged baseline guidance in `context/SECURITY.md`; always-on Kiro guidance; a manual Kiro security-review workflow; allow/deny policy files; the demo permission gate; fixture and E2E enforcement tests |
| **Starter integrations** | Kiro hook definitions for governance, audit capture, and clean-state reminders. Validate their end-to-end behaviour in the target Kiro environment before relying on them as enforcement. |
| **Fill per project** | Control-matrix rows, threat model, data boundaries, approval policy, security test cases, and module-local constraints |
| **Deferred** | Security-sensitive-change workflow, trigger-to-workflow mapping, required CI/CD checks, protected audit storage, and framework-specific runtime adapters |

A control should be called **mechanical** only when an execution path enforces it and tests prove that path. Steering and documentation are guidance; hooks and local checks provide feedback; CI/CD and runtime controls provide the enforceable boundaries.

## Running the Demo

```bash
python3 demo/demo.py            # With enforcement (shows ✓ and ⛔)
python3 demo/demo.py --nogate   # Same model, no enforcement (proves harness matters)
```

## Tool Compatibility

| Feature | Claude Code (active root) | Kiro (opt-in: copy `kiro/`→`.kiro/`) | Codex / Copilot / Cursor / Gemini |
|---------|------------|------|-----------------------------------|
| Instruction file | `CLAUDE.md` (auto-loaded; imports `@AGENTS.md`) | `CLAUDE.md` (manual ref) | `AGENTS.md` (auto-loaded) |
| Enforcement hooks | `.claude/settings.json` → `governance/permission.py` | `.kiro/hooks/*.json` → same `permission.py` | N/A (call `permission.py` CLI) |
| Always-on rules | `.claude/rules/*.md` (CLAUDE.md priority) | `.kiro/steering/*.md` (`inclusion: auto`) | — |
| Session workflow | `.claude/commands/session-cycle.md` (`/session-cycle`) | `.kiro/steering/session-cycle.md` | — |

**Claude-first, Kiro opt-in.** The active root is wired for Claude Code — nothing in
it is inert. Kiro's integration lives under `kiro/`; a Kiro user copies it to `.kiro/`
to activate (see `kiro/README.md`). Both runtimes invoke the **same** tool-agnostic
`governance/permission.py` — only the activation layer differs.

**Why `AGENTS.md`?** It's the open standard read by other agents (Codex, Cursor,
Copilot, Gemini, Aider, Windsurf, Zed) and defines system identity. Claude Code reads
`CLAUDE.md`, not `AGENTS.md` — so `CLAUDE.md` imports it via `@AGENTS.md`, giving one
source of truth that loads in every runtime.

> **Enforcement caveat (verified this template revision):** the mechanical gate is
> real, but the hook *wiring* is what activates it. The Claude hook path is proven by
> `tests/test_hooks.py`. The Kiro hook payload wiring must be confirmed inside a real
> Kiro runtime — see `kiro/hooks/governance-check.json`.

## References & Lineage

Core framing: **agent = model + tools; harness = everything else.**

| Resource | Role |
|----------|------|
| [Learn Harness Engineering](https://walkinglabs.github.io/learn-harness-engineering/en/) | The "why." 13-lecture course on harness theory. ([repo](https://github.com/walkinglabs/learn-harness-engineering)) |
| [Awesome Harness Engineering](https://github.com/Jiaaqiliu/Awesome-Harness-Engineering) | Curated primary-source map. Core framing. |
| [Awesome Claude Code](https://github.com/hesreallyhim/awesome-claude-code) | The "how" — CLAUDE.md, hooks, subagents. |
| "Harness Engineering: Leveraging Codex in an Agent-First World" (OpenAI) | Coined the term. |
| [Claude Code on AWS Bedrock — Best Practices](https://github.com/timwukp/claude-code-on-aws-bedrock-best-practices) | Fail-closed hooks, managed-settings, red-team suite. |
