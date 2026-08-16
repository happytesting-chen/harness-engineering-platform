# Security Control Matrix

Complete only the rows that apply to the copied project's approved design. The matrix links a security objective to its implementation, verification, and review evidence.

**How to read the Status column.** A control is **MECHANICAL** only when an execution path
enforces it *and* a test proves that path. Anything else is named honestly:

| Status | Meaning |
|---|---|
| **MECHANICAL** | code enforces it, a test proves it — open the file and the test |
| **OBSERVE** | it can detect and flag, but cannot prevent. Never hang a guarantee here |
| **LIBRARY** | the code exists and is tested, but **no execution path calls it yet** |
| **GAP** | nothing implements it. An unstated gap is an unmanaged risk |

The chain each row asserts is: **threat → objective → mechanism → code → proof**. A row
whose Verification column is empty is a claim, not a control.

## Template baseline (shipped, verified 2026-08-10)

These rows describe what the template enforces before any project tailoring. Verification
commands are runnable as-is from the project root.

| Control ID | Objective and boundary | Implementation location | Verification | Review evidence |
|---|---|---|---|---|
| `SEC-EGRESS-001` | **MECHANICAL** — blocks five known network shell tokens (`curl`, `wget`, `nc`, `ssh`, `nmap`) in `bash` commands whose host is not in `egress_hosts`. **Scope deliberately narrow:** this is a token blocklist, not destination control — `ncat`, a tab separator, or an interpreter fetch all pass, and `WebFetch` never reaches this gate. The remainder is `SEC-EGRESS-GAP-001` | `governance/mcp-allowlist.json`, `governance/permission.py` `check_egress` | `python3 tests/test_fixtures.py` | Egress policy review |
| `SEC-SELF-001` | **MECHANICAL** — the agent cannot rewrite the mechanism that constrains it (S2.4). Matched on file *identity*, so `../`, absolute paths, symlinks, hard links and case variants all collapse to the same target | `governance/permission.py` `check_protected_paths` + `BUILTIN_PROTECTED_PATHS` | `python3 -m pytest tests/test_protected_paths.py -q` | Gate 1a review; `SECURITY.md` S2.4 |
| `SEC-POLICY-001` | **MECHANICAL** — an unreadable or unparseable policy file yields no verdict, so it must DENY (exit 2), never error open | `governance/permission.py` `PolicyError`, `_load_json` | `python3 -m pytest tests/test_protected_paths.py -q` | `SECURITY.md` S2.4 "untrusted policy" note |
| `SEC-CMD-001` | **MECHANICAL** — hard-blocked command patterns never execute | `governance/deny-list.json`, `governance/permission.py` `check_deny_list` | `python3 tests/test_fixtures.py` | Deny-list policy review |
| `SEC-PHASE-001` | **MECHANICAL** — only approved tools may execute, and a tool stays locked until its prerequisite phase passes; unknown tools fail closed (`not in allowlist`). Supersedes the former `SEC-TOOL-001`, which named the same function | `governance/permission.py` `check_phase_gate`, `Harness-Best-Practice/feature_list.json` | `python3 tests/test_fixtures.py` | Phase sign-off record; tool/version approval |
| `SEC-SECRET-001` | **MECHANICAL** — credentials cannot be written into the repo. **Limits:** regex/AST patterns over named fields; catches the shipped pattern set, not all credentials | `Security-kit/secret_scan.py` `main` (PreToolUse hook) | `python3 -m pytest tests/test_hooks.py -q` | Secret-scan pattern review |
| `SEC-HOOK-001` | **MECHANICAL** — the gate is actually wired, not merely correct. Only `exit 2` blocks; every other outcome silently allows | `.claude/settings.json` PreToolUse | `python3 -m pytest tests/test_hooks.py -q` | Hook wiring review |
| `SEC-AUDIT-001` | **OBSERVE** — every verdict is recorded append-only. PostToolUse cannot veto, so this is accountability, not prevention | `Harness-Best-Practice/observability/audit.py` `record` | `python3 -m pytest tests/test_hooks.py -q` | Audit-log review cadence |
| `SEC-CONTENT-001` | **LIBRARY** — screens untrusted *content* (claim bodies, emails, retrieved docs) for injected control fields and instruction-shaped text. Tested, but **no ingestion path calls it yet**; it reports, never obeys | `Security-kit/content_trust.py` `screen_record` | `python3 -m pytest tests/test_content_trust.py -q` | Wire-up decision still open |
| `SEC-COVERAGE-001` | **MECHANICAL** — every control marked `applies` maps to a row here with a real verification. Enforces *completeness*, not *adequacy* | `Security-kit/check_coverage.py` `check` in `./init.sh` | `./init.sh` | Coverage gate output |
| `SEC-TAILOR-Z3` | **OBSERVE, and deliberately not more.** `/security-tailor` is a Zone-3 *drafter* (nondeterministic, human-present): it proposes an applicability classification and drafts `coverage.json` / `active-controls.md`. A prompt has **no enforcement power** — what makes the output safe is `check_coverage.py` refusing a bad draft, plus a human accepting the residual risk. What IS mechanical here is that the prompt still carries its five guardrails, injection-boundary included. **Why that text is load-bearing rather than decorative:** this drafter reads `Context/` — prose from outside the repo — and its output feeds `active-controls.md`, which `CLAUDE.md` `@`-imports into every later agent session. The mechanical screen for that ingestion, `content_trust.py`, exists and **nothing calls it** (`SEC-CONTENT-001`). So at the one point untrusted prose enters this kit, one English sentence is the entire boundary, and I5 checks that the sentence is still there | `.claude/commands/security-tailor.md` and `kiro/steering/security-tailor.md` guardrails; `Security-kit/check_coverage.py` `check_i5` | `python3 tests/test_mechanisms.py` | Runtime spec §11 four-zone table (Zone 3 — drafting); conceptual design §2.3 |

## Known gaps in the shipped template

Recorded here because an unstated gap is an unmanaged risk. Each was **measured**, not
assumed — the tool name and observed behaviour are given so the claim is checkable.

| Control ID | Objective and boundary | Implementation location | Verification | Review evidence |
|---|---|---|---|---|
| `SEC-COVER-GAP-001` | **GAP** — the two preventive hooks match only the five file/shell tools (`Bash`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`). Measured: `permission.py` *would* deny `WebFetch`, `Agent`, `CronCreate` and `mcp__github__push_files` (it returns `not in allowlist`, and even `protected path (S2.4)` for an MCP write to the gate) — but the matcher never routes them there. The deny-list is bypassed by **choosing another tool**, not by defeating a check. The gate is correct and *not there* | `.claude/settings.json` matcher | none — no test covers unmatched tools | Fix: `matcher` → `'*'` + internal allowlist. Needs its own commit + test |
| `SEC-EGRESS-GAP-001` | **GAP** — egress is checked only for `bash`, by substring-matching five tokens (`curl `, `wget `, `nc `, `ssh `, `nmap `). `WebFetch` is a complete egress channel with no egress check, and an interpreter (`python3 -c "import urllib…"`) bypasses the token match | `permission.py` `check_egress` (reached only when `tool == "bash"`) | partial — shell forms only | Accept as residual risk or extend to URL-bearing args |
| `SEC-PROMPT-GAP-001` | **GAP, and an unused attach point rather than a missing capability.** Claude Code offers `UserPromptSubmit`, which *can* block — exit 2 "blocks prompt processing and erases the prompt" ([code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks), read 2026-08-10). This template wires none, so nothing inspects a prompt before it reaches the model. Note that wiring one buys `OBSERVE`, not a guarantee: it pattern-matches, and a paraphrase defeats a pattern | — | none | Cheap to add for prompt-entry logging. Do not claim it as injection prevention |
| `SEC-INTERP-GAP-001` | **GAP** — an interpreter one-liner can open a protected file for writing without using any deny-listed shell token. Deliberately **pinned by a test** so it cannot close silently without the docs changing | `governance/deny-list.json` (pattern-based, incomplete by construction) | `tests/test_protected_paths.py::test_interpreter_write_is_a_known_documented_gap` | `SECURITY.md` S2.4 residual-gap note |
| `SEC-RESULT-GAP-001` | **GAP, and unlike the prompt gap it cannot be closed with a hook.** Nothing preventive stands where a tool *result* re-enters the model (position ④): `PostToolUse` is the only event there and the docs state it cannot block — the tool already ran. So injected text in a DB row, an email or a fetched page reaches the context window unscreened, and models weight tool output highly | `.claude/settings.json` PostToolUse (observe-only); `Security-kit/content_trust.py` exists but is unwired | none | Screening must live *inside* the code that reads the content — hence `content_trust.py` is a library you call. Even wired it is `OBSERVE` |
| `SEC-SEQUENCE-GAP-001` | **GAP** — the gate is a **stateless per-call check**, so it is blind by construction to anything that lives in the sequence rather than the call. Twenty individually-legal actions each pass; there is no session-cumulative counter, budget, or turn cap on the production path (`max_turns` is `demo/harness.py:47`, and the demo is not the enforcement path). The 3-strike stop in `CLAUDE.md` has no code | `governance/permission.py` holds no cross-call state | none | Spec §4 A2 (session-cumulative state) — specified, not built |
| `SEC-PHASE-GAP-001` | **GAP** — phase sign-off is convention, not mechanism. `check_phase_gate` trusts `status: "passing"` in `feature_list.json`, which is **not** a protected path. Measured: an Edit to it returns ALLOW, and flipping the field takes the gated tool from BLOCK to ALLOW. Nothing verifies a *human* set it, so memory-poisoning is also privilege escalation | `permission.py` `check_phase_gate` reads `Harness-Best-Practice/feature_list.json` | none — no test covers self-promotion | Fix: add the file to `BUILTIN_PROTECTED_PATHS`, or require a signed sign-off record. Weigh against the agent needing to update its own progress |
| `SEC-RUNTIME-GAP-001` | **GAP** — everything above protects the agent that *builds* the product. A **deployed** agent has no hook system: nothing emits events, so the dispatcher is code you write and every tool call must route through it | design only — `Security-kit/runtime/` does not exist | none | `docs/superpowers/specs/2026-08-13-security-kit-build-design.md` |
| `SEC-PROOF-GAP-001` | **GAP** — a *named* proof that disappears is silent. Measured 2026-08-15: `init.sh` names all 9 of `tests/test_*.py` individually and invokes no glob runner, so I3's reachability half is satisfied — but each block is `if [ -f … ]` with **no `else`**, so renaming or deleting a test file removes its check without changing the build's verdict. The full-suite runner that would catch it lives in CI (`.github/workflows/harness-baseline.yml:77-101`), not in `init.sh`, deliberately: keeping `./init.sh` pytest-free is what makes the per-file wiring the zero-dependency path | `init.sh` block 5b names tests individually; `[ -f ]` with no `else` | none — measured by hand | Fix: a required-set list for the 9 files, so a missing one is an ERROR. Block `(b2)` does this for `test_protected_paths.py` only; the other 8 are still owed (§6.2 item 12(b)) |
| `SEC-HARDEN-GAP-001` | **GAP** — `/runtime-harden`, the second Zone-3 drafter, is specified in three design docs and exists nowhere. Measured 2026-08-11: no file matches `*harden*` on any host, and `Security-kit/runtime/` is absent. So the deployed-runtime half of the kit has neither its library nor its drafter. Nothing is falsely claimed — the row exists so the absence is stated rather than assumed | design only — no file | none | Create the file and add it to `ZONE3_DRAFTERS` in the same commit; `SEC-RUNTIME-GAP-001` tracks the library |
| `SEC-KIRO-GAP-001` | **GAP** — the Kiro host's Zone-3 drafter is checked by **text presence only**. Its five guardrails now match I5 (fixed 2026-08-15, from a measured 2/5), but no test drives a Kiro session, and `inclusion: auto` is asserted by the presence of a frontmatter key — nothing verifies that Kiro loaded the file, or that a Kiro-hosted `/security-tailor` run obeyed a word of it. Claude-host-only verification is a scoping decision, not a claim the mirror is safe | `kiro/steering/security-tailor.md`; `kiro/steering/active-controls.md` | `python3 tests/test_mechanisms.py` covers guardrail *text*, nothing covers host *behaviour* | Fix: a Kiro-host integration proof, or accept as residual and say so at sign-off |

## Per-project rows

| Control ID | Objective and boundary | Implementation location | Verification | Review evidence |
|---|---|---|---|---|
| `SEC-XXX-001` | **GAP** — {{PROJECT_SPECIFIC_SECURITY_OBJECTIVE}} | {{IMPLEMENTATION_LOCATION}} | {{VERIFICATION_COMMAND}} | {{REVIEW_RECORD_OR_DECISION}} |

## Completion Rules

- Use stable IDs so features, tests, and review records can reference the same control.
- Add a row when a feature introduces or changes a trust boundary, tool, external service, identity rule, sensitive data flow, or deployment control.
- Link evidence; do not claim that a control is enforced without a mapped verification.
- State gaps explicitly. A `GAP` row with an owner is managed; a missing row is not.
- Do not upgrade a row to **MECHANICAL** without naming the test that proves the path.
