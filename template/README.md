# Harness Engineering Template

The generic, domain-agnostic harness skeleton. Copy this directory to start
any new agent project — then fill in the `{{placeholders}}` with your domain
expert's content.

## How to use

```bash
cp -r template/ examples/my-new-agent/
cd examples/my-new-agent/
# Fill in AGENTS.md, feature_list.json, deny-list.json, mcp-allowlist.json,
# and add domain docs to context/
```

## What's generic (don't modify per project)

| File | Role | Layer |
|---|---|---|
| `harness.py` | Agent loop | Lifecycle |
| `governance/permission.py` | Permission gate mechanism | Governance |
| `observability/audit.py` | Append-only audit log | Observability |
| `init.sh` | Startup verification (auto-detects stack) | Verification |

## What's customised (fill in per project)

| File | Role | Who fills it |
|---|---|---|
| `AGENTS.md` | Entry point — purpose, verify commands, escalation | Domain expert + AI engineer |
| `feature_list.json` | Phase DAG with acceptance criteria | Domain expert |
| `governance/deny-list.json` | Hard-deny patterns | Domain expert |
| `tools/mcp-allowlist.json` | Permitted tools + phase gates | Domain expert |
| `context/` | Knowledge docs (methodology, scope, standards) | Domain expert |
| `progress.md` | Session continuity log | Updated every session |

## Verification

```bash
# From a filled-in project:
python3 -m pytest tests/
```

## Examples

See `../examples/` for filled-in instances:
- `red-team-harness/` — offensive security / penetration testing agent
- (more to come: secure-ai-harness, sast-agent, etc.)
