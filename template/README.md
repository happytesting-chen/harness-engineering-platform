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
| `CLAUDE.md` | `{{PROJECT_NAME}}`, `{{PROJECT_PURPOSE}}`, `{{VERIFICATION_COMMAND}}` | Claude Code reads this — defines session workflow and working rules |
| `AGENTS.md` | `{{PROJECT_NAME}}`, `{{TECH_STACK}}`, `{{HARD_CONSTRAINTS}}` | Open standard — defines what this system is, how to run/verify it (Codex, Copilot, Cursor, Gemini) |
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
├── .claude/
│   ├── settings.json         ← Hook config (production enforcement)
│   └── commands/
│       ├── session-cycle.md  ← Generic session workflow
│       └── domain-workflow.md← Domain-specific placeholder
│
└── .kiro/
    ├── hooks/
    │   ├── governance-check.json  ← Permission gate (preToolUse)
    │   ├── secret-block.json      ← Credential detection (preToolUse)
    │   ├── audit-capture.json     ← Audit logging (postToolUse)
    │   └── clean-state-check.json ← Session hygiene (agentStop)
    └── steering/
        ├── session-cycle.md       ← Auto-included session workflow
        └── domain-workflow.md     ← Manual-include domain placeholder
```

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

## Running the Demo

```bash
python3 demo/demo.py            # With enforcement (shows ✓ and ⛔)
python3 demo/demo.py --nogate   # Same model, no enforcement (proves harness matters)
```

## Tool Compatibility

| Feature | Claude Code | Kiro | Codex / Copilot / Cursor / Gemini |
|---------|------------|------|-----------------------------------|
| Instruction file | `CLAUDE.md` (auto-loaded) | `CLAUDE.md` (manual ref) | `AGENTS.md` (auto-loaded) |
| Enforcement hooks | `.claude/settings.json` (5 hooks) | `.kiro/hooks/*.json` (4 hooks) | N/A (use permission.py CLI) |
| Session workflow | `.claude/commands/session-cycle.md` (`/session-cycle`) | `.kiro/steering/session-cycle.md` (`inclusion: auto`) | — |
| Domain workflow | `.claude/commands/domain-workflow.md` (placeholder) | `.kiro/steering/domain-workflow.md` (`inclusion: manual`) | — |

**Why both `.claude/` and `.kiro/`?** Each tool reads from its own expected location. The template ships parallel content in both formats so enforcement and workflows fire regardless of which runtime you use. Same governance logic, different integration points.

**Why `AGENTS.md` too?** It's the Linux Foundation open standard read by 60k+ repos (Codex, Cursor, Copilot, Gemini CLI, Aider, Windsurf, Zed). Defines system identity — different from CLAUDE.md's session workflow.

## References & Lineage

Core framing: **agent = model + tools; harness = everything else.**

| Resource | Role |
|----------|------|
| [Learn Harness Engineering](https://walkinglabs.github.io/learn-harness-engineering/en/) | The "why." 13-lecture course on harness theory. ([repo](https://github.com/walkinglabs/learn-harness-engineering)) |
| [Awesome Harness Engineering](https://github.com/Jiaaqiliu/Awesome-Harness-Engineering) | Curated primary-source map. Core framing. |
| [Awesome Claude Code](https://github.com/hesreallyhim/awesome-claude-code) | The "how" — CLAUDE.md, hooks, subagents. |
| "Harness Engineering: Leveraging Codex in an Agent-First World" (OpenAI) | Coined the term. |
| [Claude Code on AWS Bedrock — Best Practices](https://github.com/timwukp/claude-code-on-aws-bedrock-best-practices) | Fail-closed hooks, managed-settings, red-team suite. |
