# Kiro Add-On (opt-in)

This folder holds the **Kiro-specific** integration for the harness. Claude Code
does not read anything under `kiro/` — it uses `.claude/` and `CLAUDE.md`. Keeping
Kiro's files here means the active project root contains nothing inert for Claude.

## Activate for Kiro

Copy this folder's contents into a `.kiro/` directory at the project root:

```bash
cp -r kiro/ .kiro/
```

Kiro then auto-loads:
- `.kiro/steering/*.md` — session-cycle (auto), domain-workflow (manual),
  security + security-review guidance
- `.kiro/hooks/*.json` — governance, secret-block, audit-capture, clean-state

## What's shared vs tool-specific

- **Shared, tool-agnostic:** `governance/permission.py`, `governance/deny-list.json`,
  `governance/mcp-allowlist.json`, `Harness-Best-Practice/observability/audit.py`, `feature_list.json`,
  `tests/`. Both runtimes invoke these; they live in the project root, not here.
- **Kiro-specific (here):** the `.kiro/` hooks and steering that wire those shared
  mechanisms into Kiro's lifecycle. The Claude equivalents live in `.claude/`.

## Note on the hooks

`hooks/governance-check.json` invokes the same `governance/permission.py` gate the
Claude hook uses. Verify hook behavior inside a real Kiro runtime before relying on
it as enforcement — hook payload wiring differs between runtimes and cannot be
tested from Claude Code.
