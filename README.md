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

All tasks complete (1–14). Template fully functional with tests passing. Red Team example demonstrates the platform applied to authorized penetration testing.

## References & Lineage

Core framing: **agent = model + tools; harness = everything else.**

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
