# Security Manifest

The authoritative inventory of **what in this template is security** and what is not.
Use it to (a) review the security layer in isolation, (b) compare a with-security vs
no-security build, and (c) drive `install.sh --no-security`.

Terminology note: the `governance/` **directory is security** — it is the enforcement
(control + data plane). "Governance" in the *project-management* sense (phases, WIP=1,
human sign-off) is workflow and lives in `Harness-Best-Practice/feature_list.json` + `CLAUDE.md`. The word is
overloaded; this manifest uses **security = enforcement + its policy/guidance/tests**.

---

## Tier 1 — Pure security (movable; removed by `--no-security`)

These exist only for security. A no-security build deletes them.

| Path | Role | OWASP |
|------|------|-------|
| `governance/permission.py` | Control-plane gate (protected paths → deny-list → phase-gate → egress) | LLM06, ASI02/05 |
| `governance/runtime_dispatcher.py` | In-process chokepoint for a **deployed** app — gates ② ③ ④ with no hooks | LLM06, ASI02/05 |
| `Security-kit/content_trust.py` | Data-plane boundary (injection screening) — owns `_INJECTION_MARKERS` | LLM01/05, ASI01/06 |
| `Security-kit/prompt_screen.py` | Pre-model input screen, UserPromptSubmit adapter (①) | LLM01, ASI01 |
| `Security-kit/result_screen.py` | Pre-model tool-output screen, PostToolUse adapter (④) | LLM01/05, ASI01 |
| `Security-kit/runtime_screen.py` | Same ① and ④ screens as in-process calls for a deployed app | LLM01/05, ASI01 |
| `Security-kit/secret_scan.py` | Secret-block hook adapter | LLM02, LLM07 |
| `governance/deny-list.json` | Hard-blocked patterns (policy) | ASI05 |
| `governance/mcp-allowlist.json` | Tool + egress allowlist (policy) | LLM03, ASI02/03/04 |
| `Harness-Best-Practice/observability/audit_hook.py` | PostToolUse audit adapter | ASI09/10 |
| `Security-kit/SECURITY.md` | 42-control reference (source-tagged, S1.1–S8.6) | all |
| `Security-kit/` (this dir) | Kit navigation, control matrix, crosswalk | all |
| `tests/test_fixtures.py`, `tests/fixtures.json` | Gate ground-truth tests | LLM06 |
| `tests/test_e2e.py` | End-to-end enforcement proof | LLM06 |
| `tests/test_hooks.py` | Hook-integration proof (Claude path) | LLM01/02 |
| `tests/test_content_trust.py` | Data-plane proof | LLM01 |
| `tests/test_prompt_screen.py` | ① input-screen proof (exit 2 erases the prompt) | LLM01, ASI01 |
| `tests/test_result_screen.py` | ④ output-substitution proof (`updatedToolOutput`, shape-preserving) | LLM01/05, ASI01 |
| `tests/test_result_screening.py` | ④ end-to-end screening behaviour | LLM01/05 |
| `tests/test_runtime_screen.py` | Deployed-runtime ① and ④ proof (fail-closed, non-`str` rejected) | LLM01/05, ASI01 |
| `tests/test_runtime_dispatcher.py` | Deployed-runtime ② ③ ④ proof (`calls == 0` after a ② denial) | LLM06, ASI02/05 |
| `tests/test_protected_paths.py` | Gate 1a self-protection proof (file identity, not spelling) | ASI09/10 |
| `tests/test_egress.py` | Gate 3 egress proof (shell tokens + structured fields) | LLM02, ASI05 |
| `tests/test_injection_corpus.py` | Detection recall/precision against the labelled corpus | LLM01, ASI01 |
| `tests/test_shipped_policy.py` | The policy files as shipped, not as fixtured | LLM03, ASI04 |
| `tests/test_steady_state.py` | Phase-gate escalation attempts all DENY | ASI09 |
| `Security-kit/runtime/semantic-model.lock.json` | Human-signed classifier pin (artifact digests, corpus digest, confidence floor) | LLM01 |
| `Security-kit/runtime/semantic-model.schema.json` | Lock-file schema (documentation of the contract) | LLM01 |
| `Security-kit/eval/runtime_injection/`, `Security-kit/eval/eval_runtime_injection.py` | Labelled corpus + benchmark/verify runner | LLM01 |
| `Security-kit/runtime/__init__.py` | runtime-mvp semantic tier — package exports | all |
| `Security-kit/runtime/adapters.py` | runtime-mvp semantic tier — runtime-mvp entry points (①/④ in process) | LLM01, ASI01 |
| `Security-kit/runtime/attack_driver.py` | runtime-mvp semantic tier — 13-class attack matrix + deterministic replay (evaluation tooling) | all |
| `Security-kit/runtime/audit.py` | runtime-mvp semantic tier — hash-chained, closed-schema evidence | ASI09/10 |
| `Security-kit/runtime/classifier.py` | runtime-mvp semantic tier — pinned local classifier protocol + lock verification | LLM01 |
| `Security-kit/runtime/contracts.py` | runtime-mvp semantic tier — closed enums, frozen types, typed receipts | all |
| `Security-kit/runtime/guarded.py` | runtime-mvp semantic tier — ⑤ ceilings, origin rules, schema — composed around ② | LLM06, ASI02/08 |
| `Security-kit/runtime/host.py` | runtime-mvp semantic tier — the owned single-agent loop | all |
| `Security-kit/runtime/ingress.py` | runtime-mvp semantic tier — the binding ALLOW/REQUIRE_REVIEW decision table | LLM01, ASI01 |
| `Security-kit/runtime/normalization.py` | runtime-mvp semantic tier — NFKC, zero-width/bidi stripping-as-signal, bounded chunking | LLM01 |
| `Security-kit/runtime/output.py` | runtime-mvp semantic tier — buffered final-output redaction | LLM02, LLM07 |
| `Security-kit/runtime/review.py` | runtime-mvp semantic tier — content-release and action-approval receipts, domain-separated keys | ASI09 |
| `Security-kit/runtime/review_cli.py` | runtime-mvp semantic tier — inert reviewer surface | ASI09 |
| `Security-kit/runtime/rules.py` | runtime-mvp semantic tier — adapter over content_trust.scan_text — never returns data | LLM01 |
| `Security-kit/runtime/session.py` | runtime-mvp semantic tier — reserve/commit/rollback session state | ASI08 |
| `Security-kit/runtime/startup.py` | runtime-mvp semantic tier — refuse-to-start invariants | ASI08 |
| `tests/runtime/test_action_receipts.py` | approval never converts DENY; exact digest; single-use | ASI09 |
| `tests/runtime/test_audit.py` | chain detects tampering AT the doctored record | ASI10 |
| `tests/runtime/test_claims_truthfulness.py` | docs cannot drift ahead of code | all |
| `tests/runtime/test_classifier.py` | 13 failure shapes → UNRESOLVED; lock drift refuses | LLM01 |
| `tests/runtime/test_content_receipts.py` | type/key/context separation | ASI09 |
| `tests/runtime/test_contracts.py` | closed enums, frozen types | all |
| `tests/runtime/test_design_contract.py` | profile vocabulary pinned | all |
| `tests/runtime/test_guarded.py` | ceilings under thread + asyncio races; inner gate still fires | ASI08 |
| `tests/runtime/test_host.py` | startup-gated loop; nothing unapproved enters context | all |
| `tests/runtime/test_ingress.py` | the decision table, row by row; classifier.calls == 0 on rule hit | LLM01 |
| `tests/runtime/test_ingress_adapters.py` | malformed → review, never pass | LLM01 |
| `tests/runtime/test_normalization.py` | deterministic; reject-never-truncate | LLM01 |
| `tests/runtime/test_output.py` | zero bytes before screening; no echoed match | LLM02 |
| `tests/runtime/test_replay.py` | 13/13 RESISTANT; fooled classifier still RESISTANT | all |
| `tests/runtime/test_review_cli.py` | ANSI/markup neutralized; no content in receipt | ASI09 |
| `tests/runtime/test_rules.py` | never returns data; owns no pattern | LLM01 |
| `tests/runtime/test_source_sink_paths.py` | every profile row, scored on side effects | all |
| `tests/runtime/test_startup.py` | every disabled capability is a StartupError | ASI08 |
| `kiro/steering/security.md`, `kiro/steering/security-review.md` | Kiro security guidance/workflow | all |
| `kiro/hooks/*` | Kiro enforcement hooks | LLM06 |
| `Security-kit/check_coverage.py` | Coverage gate (init.sh block 5b) | all |
| `Security-kit/coverage.json` (generated) | Per-project control applicability output | all |
| `Security-kit/coverage.schema.md` | coverage.json field contract | all |
| `Security-kit/active-controls.md` | Layer-D steering (agent loads every session) | all |
| `Security-kit/eval/` | Selection benchmark corpus + eval_selection.py | all |
| `tests/test_coverage.py` | Coverage-gate unit + integration tests | LLM06 |
| `tests/test_eval_selection.py` | Selection benchmark recall test | all |
| `.claude/commands/security-tailor.md` | `/security-tailor` slash command (explicit Tier 1 — outside Security-kit/ dir) | all |
| `kiro/steering/security-tailor.md` | Kiro security-tailor steering (explicit Tier 1 — outside Security-kit/ dir) | all |
| `kiro/steering/active-controls.md` | Layer-D steering mirror for the Kiro host (explicit Tier 1 — outside Security-kit/ dir) | all |
| `Security-kit/mechanisms.json` | Claims register — what each mechanism is, joined by I1–I4 | all |
| `Security-kit/requirements.json` | Requirement spine — obligations, severity, residuals; joined by I6 | all |
| `tests/test_mechanisms.py` | I1–I5 invariant tests + the matrix census | all |
| `tests/test_requirements.py` | I6 invariant tests, both directions | all |

> Note on `install.sh`: `TIER1` deletes whole **directories** — `governance`, `Security-kit`, `tests` among them — so every path above that sits inside one of those needs **no** explicit `TIER1` entry. That covers all of `Security-kit/` (`check_coverage.py`, `coverage.json`, `coverage.schema.md`, `active-controls.md`, `eval/`, `mechanisms.json`, `requirements.json`, the three screen modules), all of `governance/` (`runtime_dispatcher.py` included), the whole `Security-kit/runtime/` package, and every `tests/test_*.py` and `tests/runtime/test_*.py` listed here. Only `.claude/commands/security-tailor.md`, `kiro/steering/security-tailor.md` and `kiro/steering/active-controls.md` require explicit entries: `kiro/steering/` is not one of the deleted directories.
>
> Consequence worth stating: adding a security module under `governance/` or `Security-kit/` needs a row **here** but no `install.sh` edit. The manifest is the only place that would notice it missing.

## Tier 2 — Pure harness / non-security (kept in every build)

Project-management and evaluation scaffolding. No security role.

| Path | Role |
|------|------|
| `Harness-Best-Practice/AGENTS.md` | Agent identity (open standard) |
| `Harness-Best-Practice/progress.md` | Session journal + handoff |
| `Harness-Best-Practice/BEST-PRACTICES.md` | Harness engineering principles (generic) |
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
| `CLAUDE.md` | startup workflow, WIP=1, verification, session end | the "Governance Boundaries" section + governance escalation lines + the layer-D HTML comment + `@Security-kit/active-controls.md` import (python3 strip in install.sh) |
| `Harness-Best-Practice/feature_list.json` | phase list (behavior/verification/status) | the same file is *read by* the phase-gate — no lines to strip, but the gate stops consuming it |
| `init.sh` | placeholder check, tests, Fresh Session Test | the "Security-kit integrity" section (block 5b) |
| `.claude/settings.json` | Stop: clean-state-check | UserPromptSubmit prompt-screen (①), PreToolUse governance-check + secret-block (②), PostToolUse result-screen (④) + audit-capture — 7 hooks across 4 events |
| `Harness-Best-Practice/observability/audit.py` | (none — pure security in practice, but demo/ imports it) | append-only decision log; kept if demo/ needs it, else Tier 1 |
| `.claude/commands/init-project.md` | Steps 1–5 project init workflow | Step 2b block (invokes `/security-tailor`; removed by install.sh — advisory doc edit, not mechanical enforcement) |
| `.claude/commands/session-cycle.md` | full session loop startup/execution/exit | step 11b block (invokes `/security-tailor`; removed by install.sh — advisory doc edit, not mechanical enforcement) |
| `kiro/steering/session-cycle.md` | full session loop startup/execution/exit | step 11b block (invokes `/security-tailor`; removed by install.sh — advisory doc edit, not mechanical enforcement) |

> Why Tier 3 exists: a gate that isn't wired into the tool-call path does nothing.
> Enforcement *is* the wiring. This is the honest boundary — you can label and toggle
> these, but you can't move them out without breaking the thing they protect.

---

## No-security build (comparison / `install.sh --no-security`)

Produces a functional harness with the security layer removed — useful for A/B
comparison or for a project that deliberately accepts no mechanical governance.

1. **Delete** all Tier 1 paths.
2. **Neutralize** Tier 3 security parts:
   - `.claude/settings.json` → keep only the Stop hooks. `install.sh` pops all three
     security events: `UserPromptSubmit`, `PreToolUse`, `PostToolUse` (install.sh:84–86).
   - `init.sh` → drop the "Security-kit integrity" block and the two governance JSON
     entries from `REQUIRED_FILES`.
   - `CLAUDE.md` → remove the Governance Boundaries section + governance escalation lines
     + the `@Security-kit/active-controls.md` layer-D import (sed strip, Step 2b).
3. Keep all Tier 2 as-is.

Deleting Tier 1 removes **both** enforcement layers, not just the hooks: `governance/` and
`Security-kit/` go with it, so `runtime_dispatcher.py` and `runtime_screen.py` are gone and
a no-security build has no in-process chokepoint for a deployed app either.

The result still passes its own `init.sh` (placeholder + tests + Fresh Session) but has
**no mechanical enforcement** — exactly the control arm used in this template's own A/B
evaluation (scored 16/24 vs 24/24 for the full build; see
`examples/claims-agent/evaluation/TEMPLATE-EVALUATION-REPORT.md`).

> Removing security should be a deliberate, recorded choice. In a **full** build,
> `init.sh`'s integrity gate prevents the kit from being *silently* stripped while still
> reporting PASS.
