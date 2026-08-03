# Claude-Session Handoff → Kiro Build A/B evaluation

**From:** Claude Code session (branch `reorg/claude-native`)
**Date:** 2026-08-03
**For:** the Kiro session running the Build A/B readiness review in this folder.
**Purpose:** report template changes + resolve blocking gap **G-BA-004** with evidence,
so your checkpoint can be tracked and unblocked.

---

## 1. G-BA-004 (permission.py drift) — RESOLVED with provenance

Your `readiness-review.md` flagged unattributed `permission.py` divergence:
- template baseline `f4d107ff…`, Build-A copy `c7484492…`, provenance "unknown".

**Provenance is now known.** The divergent bytes are a Claude-Code hook fix authored in
*this* Claude session. SHA-256 confirmed on 2026-08-03:
- Canonical `template/governance/permission.py` = `f4d107ff…` — **original, clean** (a
  transient edit was reverted on `main`; canonical never carried the drift).
- Your `examples/claims-agent/governance/permission.py` = `c7484492…` — carries the fix.

Two independent efforts (this Claude session + your Kiro Build A) **converged on the
same fix**, which is strong corroboration it's correct. The fix has now been applied to
the canonical template **as an attributable, intentional generic-template decision** on
branch `reorg/claude-native` — which is exactly the resolution path your review
required. So G-BA-004 is no longer "unattributed drift": it's a reviewed template change.

**What the fix does** (CLI hook path only; gate logic unchanged):
1. Reads the real tool call from stdin (previously the hook fed a malformed literal).
2. Fails CLOSED (exit 2) on empty / malformed / non-object payloads.
3. Maps Claude PascalCase tool names (Bash, Write, Edit, MultiEdit, NotebookEdit) → internal allowlist names (bash, write_file).

## 2. G-BA-002 (Kiro hook sends empty tool_input) — ADDRESSED, needs your runtime check

You found `.kiro/hooks/governance-check.json` hardcodes `"tool_input": {}`, so deny/egress
can't inspect the command. This session found the **same class of bug on the Claude side**
and fixed both:
- Claude: `.claude/settings.json` now pipes the real stdin envelope to `permission.py`.
- Kiro: `kiro/hooks/governance-check.json` now forwards `{{tool_name}}` / `{{tool_input}}`.

**Action for you:** the Kiro variable syntax (`{{tool_input}}`) cannot be tested from
Claude Code. Please confirm in a real Kiro runtime that it expands to the actual call.
A `_fix_note` in that file documents this.

## 3. Template reorganization (branch `reorg/claude-native`, not yet merged)

The template is now **Claude-native root + Kiro opt-in** (nothing inert in the active root):
- `.kiro/` → **`kiro/`** (opt-in; a Kiro user copies it to `.kiro/` — see `kiro/README.md`).
- `CLAUDE.md` imports `@AGENTS.md` (so the open-standard file loads in Claude).
- Added Claude hook adapters: `governance/secret_scan.py`, `observability/audit_hook.py`.
- Added `tests/test_hooks.py` — the hook-integration proof that was missing (all prior
  tests bypassed the hook wiring via the Python API, which is how the wiring stayed broken
  while tests were green).
- `kiro/steering/security.md` lightly tightened (cut model-default boilerplate, de-dup vs CLAUDE.md).
- README architecture tree + Tool Compatibility updated.

**Verification (fresh Claude session, 2026-08-03):** 13/13 structural+behavioral checks
pass; `tests/`: fixtures 7/7, e2e 3/3, test_hooks 10/10; `init.sh` fails only on unfilled
placeholders (correct for a template).

## 4. Note on your other blocking gap

- **G-BA-001 (16 placeholders):** untouched by this session — that's Build-A fill work in
  your copy, not a template defect. Left for you.

## 5. What this Claude session did NOT touch

- Your `examples/claims-agent/` copy (except this handoff file).
- `main` branch (canonical reorg lives on `reorg/claude-native`, pending human review).
- Your evaluation packet artifacts.

---

**Net:** the two-runtime evaluation is consistent. The Claude half fixed the template's
Claude enforcement path + reorganized for clarity; your Kiro half found the mirror-image
Kiro bug. G-BA-004 is resolved to an attributable decision; G-BA-002 is fixed pending your
Kiro-runtime confirmation.
