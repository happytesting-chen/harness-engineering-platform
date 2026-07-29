# Harness Engineering Platform — Template

A reusable, zero-dependency framework for building governed AI agent projects. Copy this directory to start a new agent project with mechanical enforcement controls built in.

## Quick Start

```bash
cp -r template/ my-new-agent/
cd my-new-agent/
# Fill placeholders in required files (see below)
chmod +x init.sh
./init.sh
```

## File Classification

### Mechanism Files (never modify per project)

These implement the governance engine. Identical across all harness instances.

| File | Purpose |
|------|---------|
| `governance/permission.py` | Three-gate permission check (deny-list → phase-gate → egress) |
| `observability/audit.py` | Append-only JSON-lines audit log |
| `demo/harness.py` | Agent loop for demo/testing (NOT production path) |
| `demo/fake_model.py` | Scripted model responses for zero-dependency demos |
| `tests/test_fixtures.py` | Data-driven test runner |
| `tests/test_e2e.py` | Day 4 enforcement pattern proof |

### Policy Files (customise per domain)

These contain your project-specific rules and context.

| File | Purpose | Status |
|------|---------|--------|
| `CLAUDE.md` | Agent instruction file (Claude Code reads first) | **MUST fill** |
| `feature_list.json` | Phase DAG with verification commands | **MUST fill** |
| `governance/deny-list.json` | Hard-blocked command patterns | **MUST fill** |
| `tools/mcp-allowlist.json` | Approved tools + phase gates + egress hosts | **MUST fill** |
| `context/` | Domain knowledge documents | **MUST fill** (at least one doc) |
| `progress.md` | Session continuity record | Ships pre-filled; update each session |
| `session-handoff.md` | Mid-task handoff template | Fill only when needed |

### Integration Files (pre-filled, extend per domain)

| File | Consumed By | Purpose |
|------|-------------|---------|
| `.claude/settings.json` | Claude Code | Hook configuration (PreToolUse, PostToolUse, Stop) |
| `.claude/commands/session-cycle.md` | Claude Code | Generic session workflow (slash command) |
| `.claude/commands/domain-workflow.md` | Claude Code | Domain-specific workflow placeholder |
| `.kiro/steering/session-cycle.md` | Kiro | Same session cycle in Kiro format |
| `init.sh` | Both | Startup verification script |
| `tests/fixtures.json` | Both | Ground-truth test dataset |

## Tool Compatibility

| Feature | Claude Code | Kiro |
|---------|------------|------|
| Instruction file | `CLAUDE.md` (auto-loaded) | `CLAUDE.md` (manual ref) |
| Hooks | `.claude/settings.json` | `.kiro/hooks/` |
| Skills/Commands | `.claude/commands/*.md` | `.kiro/steering/*.md` |
| Session workflow | `/session-cycle` slash command | Auto-included steering |

The template ships both formats for cross-tool compatibility. Content is identical; only the file location and format differ.

## Architecture

```
template/
├── CLAUDE.md                 ← Entry point (instruction file)
├── feature_list.json         ← Phase DAG (domain expert fills)
├── progress.md               ← Session continuity
├── init.sh                   ← Startup verification
├── governance/
│   ├── permission.py         ← [MECHANISM] 3-gate enforcement
│   └── deny-list.json        ← [POLICY] blocked patterns
├── tools/
│   ├── mcp-allowlist.json    ← [POLICY] approved tools + egress
│   └── tool-registry.md      ← Tool vetting documentation
├── observability/
│   └── audit.py              ← [MECHANISM] append-only logging
├── context/                  ← [POLICY] domain knowledge docs
├── tests/
│   ├── fixtures.json         ← Ground-truth test cases
│   ├── test_fixtures.py      ← Data-driven test runner
│   └── test_e2e.py           ← Day 4 enforcement proof
├── demo/
│   ├── harness.py            ← [MECHANISM] agent loop (eval only)
│   ├── demo.py               ← Scripted enforcement demo
│   └── fake_model.py         ← [MECHANISM] scripted LLM
├── .claude/
│   ├── settings.json         ← Hook config (production enforcement)
│   └── commands/             ← Slash commands
└── .kiro/
    └── steering/             ← Kiro steering files
```

## How Enforcement Works

**Production path:** `.claude/settings.json` hooks → `governance/permission.py` (CLI mode)

The hooks pass tool calls as JSON on stdin to `permission.py`. It evaluates three gates in order:
1. **Deny-list** — Substring match against `deny-list.json` patterns → immediate block
2. **Phase-gate** — Tool must be in `mcp-allowlist.json` + referenced phase must be "passing"
3. **Egress** — Network commands require target host in `egress_hosts` list

Exit code 0 = allow, exit code 2 = BLOCK.

## Running the Demo

```bash
python3 demo/demo.py            # With enforcement
python3 demo/demo.py --nogate   # Same model, no enforcement (proves the harness matters)
```

## References & Lineage

This platform draws on the following sources. The core framing: **agent = model + tools; harness = everything else.**

### Foundational Reading

| Resource | Role |
|----------|------|
| [Learn Harness Engineering](https://walkinglabs.github.io/learn-harness-engineering/en/) — 13-lecture course | The "why." Covers harness theory, lifecycle, and governance patterns. ([repo](https://github.com/walkinglabs/learn-harness-engineering)) |
| [Awesome Harness Engineering](https://github.com/Jiaaqiliu/Awesome-Harness-Engineering) (Jiaaqiliu) | Curated primary-source map across 12 sections. Core framing for agent vs harness separation. |
| [Awesome Claude Code](https://github.com/hesreallyhim/awesome-claude-code) (hesreallyhim) | The "how" — CLAUDE.md patterns, slash commands, hooks, subagents, and real-world configurations. |
| "Harness Engineering: Leveraging Codex in an Agent-First World" (OpenAI) | Credited with coining the term. Both Awesome repos trace lineage here. |
| Anthropic — Building Effective Agents / Long-Running Agent Harnesses | Design principles for tool-use loops, permission boundaries, and agent lifecycle. |

### Reference Implementations

| Resource | Relevance |
|----------|-----------|
| [Claude Code on AWS Bedrock — Best Practices](https://github.com/timwukp/claude-code-on-aws-bedrock-best-practices) | Secure dev kit with fail-closed hooks, managed-settings hierarchy, and red-team suite. Our guardrail + audit patterns echo this implementation. |

### Local Context

- `harness-lab/` — 7-day study repo where the patterns in this template were developed and validated.
- `examples/red-team-harness/` — First filled-in instance demonstrating the template applied to authorized penetration testing.
