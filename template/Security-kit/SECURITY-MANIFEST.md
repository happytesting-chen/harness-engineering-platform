# Security Manifest

The authoritative inventory of **what in this template is security** and what is not.
Use it to (a) review the security layer in isolation, (b) compare a with-security vs
no-security build, and (c) drive `install.sh --no-security`.

Terminology note: the `governance/` **directory is security** — it is the enforcement
(control + data plane). "Governance" in the *project-management* sense (phases, WIP=1,
human sign-off) is workflow and lives in `feature_list.json` + `CLAUDE.md`. The word is
overloaded; this manifest uses **security = enforcement + its policy/guidance/tests**.

---

## Tier 1 — Pure security (movable; removed by `--no-security`)

These exist only for security. A no-security build deletes them.

| Path | Role | OWASP |
|------|------|-------|
| `governance/permission.py` | Control-plane gate (deny-list → phase-gate → egress) | LLM06, ASI02/05 |
| `Security-kit/content_trust.py` | Data-plane boundary (injection screening) | LLM01/05, ASI01/06 |
| `Security-kit/secret_scan.py` | Secret-block hook adapter | LLM02, LLM07 |
| `governance/deny-list.json` | Hard-blocked patterns (policy) | ASI05 |
| `tools/mcp-allowlist.json` | Tool + egress allowlist (policy) | LLM03, ASI02/03/04 |
| `observability/audit_hook.py` | PostToolUse audit adapter | ASI09/10 |
| `security/SECURITY.md` | 40-control reference (source-tagged) | all |
| `security/` (this dir) | Kit navigation, control matrix, crosswalk | all |
| `tests/test_fixtures.py`, `tests/fixtures.json` | Gate ground-truth tests | LLM06 |
| `tests/test_e2e.py` | End-to-end enforcement proof | LLM06 |
| `tests/test_hooks.py` | Hook-integration proof (Claude path) | LLM01/02 |
| `tests/test_content_trust.py` | Data-plane proof | LLM01 |
| `kiro/steering/security.md`, `kiro/steering/security-review.md` | Kiro security guidance/workflow | all |
| `kiro/hooks/*` | Kiro enforcement hooks | LLM06 |

## Tier 2 — Pure harness / non-security (kept in every build)

Project-management and evaluation scaffolding. No security role.

| Path | Role |
|------|------|
| `AGENTS.md` | Agent identity (open standard) |
| `progress.md` | Session journal + handoff |
| `BEST-PRACTICES.md` | Harness engineering principles (generic, root-level) |
| `.claude/commands/session-cycle.md`, `kiro/steering/session-cycle.md` | Session workflow |
| `.claude/commands/domain-workflow.md`, `kiro/steering/domain-workflow.md` | Domain workflow placeholder |
| `demo/` | Evaluation harness (fake model, scripted demo) |
| module `ARCHITECTURE.md` files | Per-module docs |

## Tier 3 — Mixed / wired (CANNOT be physically separated)

Security is *woven into* these files at specific lines because mechanical enforcement
must sit at integration points that also serve non-security functions. `--no-security`
**neutralizes** the security parts in place rather than deleting the file.

| Path | Non-security part | Security part (what `--no-security` strips) |
|------|-------------------|---------------------------------------------|
| `CLAUDE.md` | startup workflow, WIP=1, verification, session end | the "Governance Boundaries" section + governance escalation lines |
| `feature_list.json` | phase list (behavior/verification/status) | the same file is *read by* the phase-gate — no lines to strip, but the gate stops consuming it |
| `init.sh` | placeholder check, tests, Fresh Session Test | the "Security-kit integrity" section (block 5b) |
| `.claude/settings.json` | Stop: clean-state-check | PreToolUse governance-check + secret-block, PostToolUse audit-capture |
| `observability/audit.py` | (none — pure security in practice, but demo/ imports it) | append-only decision log; kept if demo/ needs it, else Tier 1 |

> Why Tier 3 exists: a gate that isn't wired into the tool-call path does nothing.
> Enforcement *is* the wiring. This is the honest boundary — you can label and toggle
> these, but you can't move them out without breaking the thing they protect.

---

## No-security build (comparison / `install.sh --no-security`)

Produces a functional harness with the security layer removed — useful for A/B
comparison or for a project that deliberately accepts no mechanical governance.

1. **Delete** all Tier 1 paths.
2. **Neutralize** Tier 3 security parts:
   - `.claude/settings.json` → keep only the Stop hooks (no PreToolUse/PostToolUse).
   - `init.sh` → drop the "Security-kit integrity" block and the two governance JSON
     entries from `REQUIRED_FILES`.
   - `CLAUDE.md` → remove the Governance Boundaries section + governance escalation lines.
3. Keep all Tier 2 as-is.

The result still passes its own `init.sh` (placeholder + tests + Fresh Session) but has
**no mechanical enforcement** — exactly the control arm used in this template's own A/B
evaluation (scored 16/24 vs 24/24 for the full build; see
`examples/claims-agent/evaluation/TEMPLATE-EVALUATION-REPORT.md`).

> Removing security should be a deliberate, recorded choice. In a **full** build,
> `init.sh`'s integrity gate prevents the kit from being *silently* stripped while still
> reporting PASS.
