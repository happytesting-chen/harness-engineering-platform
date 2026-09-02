# Runtime Security and Semantic Enforcement — re-scoped for this template

> **Status: draft plan, not lifecycle activation.** Same authority posture as the original:
> no implementation task, lifecycle edit or task commit begins until a human separately
> authorizes the implementation lifecycle.

**Provenance.** The original plan
([2026-08-31-runtime-security-semantic-enforcement.original.md](2026-08-31-runtime-security-semantic-enforcement.original.md))
was drafted against the `security-in-action-demo` fork in a Codex workspace frozen
**2026-08-21 — one day before this template's runtime enforcement layer shipped**
(`30d8016`, PR #6). Its architecture decisions survive contact with this tree; its file
plan and three of its baseline facts do not. This document adopts the former and re-scopes
the latter. Audited against this repository 2026-08-31.

## 1. Corrected grounded baseline (supersedes original §1)

| # | Original claim | Status in this tree, verified 2026-08-31 |
|---|---|---|
| 1 | One shared marker list in `content_trust.py` | **Holds.** `_INJECTION_MARKERS` has one owner; four adapters, zero copies, anti-drift tests |
| 2 | 10/12 attacks caught, 2/12 legitimate withheld | **Holds** (`tests/test_injection_corpus.py`) |
| 3 | Hook adapters fail open on malformed envelopes | **Holds** — `prompt_screen.py` decision 3, `result_screen.py` point 4. Both hooks also carried env-var warn escapes; the ④ escape (`RESULT_SCREEN_MODE=warn`) **was removed 2026-08-31** — patch at `docs/superpowers/patches/2026-08-31-remove-result-screen-warn-escape.patch`, human-applied and committed as `8353188`, pinned by `test_warn_env_var_is_ignored`. `PROMPT_SCREEN_MODE=warn` is retained deliberately — a ① false positive locks a human out of their own prompt |
| 4 | PreToolUse matcher covers five tools | **Holds** (`SEC-COVER-GAP-001`) |
| 5 | "A production runtime package does not exist" | **Stale.** `governance/runtime_dispatcher.py` (② ③ ④) and `Security-kit/runtime_screen.py` (① ④) shipped 2026-08-22 with 37 tests; both are in `BUILTIN_PROTECTED_PATHS`. What remains open is routing (`SEC-RUNTIME-GAP-001`, SECURITY.md S1.6) and everything semantic |
| 6 | 2026-08-13 design specifies the deterministic runtime | Holds as design; partially implemented by #5 |
| 7 | Semantic note is design-only with six open decisions | **Holds** — the semantic layer is the genuinely new capability in this plan |

## 2. Architecture decisions

**AD-1 through AD-6 are adopted as written** in the original: binding ingress boundary
(`ALLOW` / `REQUIRE_REVIEW`), one strict pipeline for user and external content with
monotonic aggregation, classifier as detection never action authority, separated
content/action receipts with domain-separated HMAC keys, pinned local classifier with no
silent fallback, constrained MVP that fails startup rather than degrading.

**AD-7 (new, binding) — no second enforcement plane.** The original's `policy_core.py`,
`policy.schema.json` and `dispatcher.py` would be a second action gate beside
`permission.py` + `RuntimeDispatcher`. This template's recorded doctrine
(`governance/ARCHITECTURE.md`): a gate module must not re-implement a rule or hold a copy
of a pattern — a second implementation is a second thing to drift. Therefore:

- The action plane **extends by composition, not by editing the owners.** Both
  `runtime_dispatcher.py` and `permission.py` are protected paths; a plan whose core
  deliverable is hand-applied patches to the file under development is a bottleneck, not
  a workflow. The dispatcher already exposes the needed seams (`runtime_dispatcher.py:94`
  — injected `tools` and `result_screen`; a cleanly wrappable `execute()`), and session
  ceilings, origin rules and the `REQUIRE_APPROVAL` tier are **new sequence-plane rules,
  not copies of existing per-call rules** — so they live in new modules that wrap
  `execute()` (reserve → delegate → commit/rollback) exactly as the original's `rules.py`
  wraps `scan_text`. Only the final wiring change, if any, ships as a small human patch.
- New policy fields (ceilings, approval tiers) land in the existing
  `governance/mcp-allowlist.json` / `deny-list.json` schema, not a parallel policy file.
- The original's `Security-kit/runtime/` package path is **not resurrected** for the
  action plane. `control-matrix.md` (2026-08-22) records that the runtime modules live
  beside their build-time counterparts; the new *semantic* modules follow the same
  convention. Reversing that is a human decision to record, not a directory to create.

**AD-8 (new, decision gate) — the classifier is a dependency-class change.** This
template's standing rule is stdlib-only mechanism code. The runtime core stays stdlib;
the classifier is a separately installed local process behind the subprocess + lock
boundary (AD-5). That is a deliberate exception and must be approved as such at the
Task 1 lifecycle gate — it does not ride in silently.

## 3. Residuals the original left unstated

R-1 and R-2 were audit findings C5 and C6; R-3 was added by the 2026-08-31 audit of this
re-scope. State all three in `Context/runtime-security-profile.md` and the eventual
verdict:

- **R-1 — the classifier is the content-release authority.** Per AD-2, rule-`unresolved`
  + semantic-`data` = ALLOW: a model's label is the sole reason rule-clean content enters
  context. The "no model decides a verdict" constraint holds for the *action* gate only —
  it cannot hold for the content gate, because semantic screening is the point. A fooled
  classifier admits content; the deterministic action gate is then the only control
  standing. The replay suite's classifier-false-negative case is the proof obligation for
  that fallback, and it must stay in the attack matrix permanently.
- **R-2 — review-queue economics.** Fail-closed everywhere routes every timeout,
  `unresolved` and false positive to human review. An attacker who cannot inject can
  still flood quarantine. The profile must state a bound: queue depth limit, per-origin
  rate limit, or auto-expiry — or record unbounded review load as an accepted risk with
  an owner.
- **R-3 — the semantic layer covers the deployed profile only.** Task 7 routes
  `runtime_screen` and the dispatcher through `evaluate_ingress()`; the build-time hooks
  stay regex-only, deliberately — a `UserPromptSubmit` hook blocking seconds on a local
  model per prompt is unacceptable latency, and hook crash semantics fail open anyway.
  Consequence to state plainly: **an IDE session gets regex screening; a deployed app
  gets regex + semantic.** Anyone reading "semantic enforcement" as covering both planes
  is reading a claim this plan does not make.

## 4. Task re-scoping (original task numbers preserved)

| Task | Disposition for this tree |
|---|---|
| 1 — design reconciliation, lifecycle proposal | **Keep**, plus: correct original baseline #5 in both specs; record AD-7/AD-8; the two residuals above go into the profile. The 2026-08-17 spec's stale measurements are corrected as written |
| 2 — contracts | **Keep as written** (`ContentEnvelope`, decisions, receipts). New module, no conflicts |
| 3 — normalization, obfuscation signals, chunking | **Keep as written** — net-new capability |
| 4 — rule layer over `scan_text` | **Keep as written** — already respects the single-owner rule. Note: `content_trust.py` is a protected path; the marker-ID additions ship as a human-applied patch |
| 5 — pinned local classifier + benchmark | **Keep as written**, gated by AD-8 approval at Task 1 |
| 6 — strict ingress aggregation, quarantine, content receipts | **Keep as written**, plus R-2's queue bound |
| 7 — adapter integration | **Keep intent, adjust targets**: the deployed entry points are `runtime_screen.screen_input()` / `screen_result()` and `RuntimeDispatcher` — route them through `evaluate_ingress()` rather than adding a third entry path. Build-time hooks stay regex-only (residual R-3). `prompt_screen.py` / `result_screen.py` / `content_trust.py` edits are human-applied patches (protected paths). The demo-fork file `security_demo/adapters.py` does not exist here — drop it |
| 8 — action policy, session, dispatcher, guard | **Re-scope per AD-7**: new modules **compose around** `RuntimeDispatcher.execute()` — session ceilings (reserve/commit/rollback), origin-sensitive rules and schema binding wrap the existing chokepoint via its constructor seams; neither `runtime_dispatcher.py` nor `permission.py` is edited except, at most, one small human-patched wiring change. Do **not** create `policy_core.py` / `dispatcher.py` / `guard.py` as parallel implementations. The default-deny and `calls == 0` test obligations stay exactly as written |
| 9 — action receipts + startup isolation | **Keep**, targeting the extended dispatcher. `REQUIRE_APPROVAL` → receipt → continued policy evaluation; a receipt never converts DENY. This closes the tiered-policy roadmap row (`SEC-HARDEN-GAP-001` names the missing drafter; the mechanism half lands here) |
| 10 — audit + buffered output | **Keep as written**; reconcile with the existing append-only `audit.py` conventions rather than a second audit format |
| 11 — owned host | **Keep**, built on the extended dispatcher; the example lands in `examples/runtime-security-mvp/` |
| 12 — break, replay, sign | **Keep as written**, including "keep `SEC-RUNTIME-GAP-001` at GAP until implementation and pre-production proof both exist". All claims changes — matrix tokens, register rows, requirements, and the `BUILTIN_PROTECTED_PATHS` additions — land here as one human-applied batch (see §5) |

**Schedule:** the original's eight-week estimate (§5 there) is **superseded** — it priced
building the action plane from scratch in weeks 5–6, which AD-7 removes. Re-estimate at
the Task 1 lifecycle gate; the deleted work is roughly offset by the human-patch
round-trips this tree's protected-path rule adds.

**Original §7 (deferred scope) stands in full** — persistent memory, delegation, binary
extraction, remote classifiers, multi-host, streaming, auto-learning all remain out, each
requiring its own approved plan.

## 5. Constraints inherited from this template (additive to original globals)

- Protected paths are never edited by an agent: `content_trust.py`, both hook screens,
  `runtime_screen.py`, `runtime_dispatcher.py`, `permission.py`, both policy JSONs,
  `.claude/settings.json`. Every task touching one emits a patch for human application;
  the per-task commit steps assume the patch has been applied and reviewed.
- `mechanisms.json` and `requirements.json` are human-owned at merge time. Tasks produce
  proposed register rows in the commit message, never direct edits.
- **Claims land once, at Task 12, as one human-applied batch.** Invariant I4
  (`check_coverage.py`) errors on any non-GAP matrix row without a register row — so a
  task that promoted a matrix row mid-plan would turn every subsequent per-task
  `./init.sh` gate red until a human edited two other files. Therefore: Tasks 1–11 touch
  neither `control-matrix.md` status tokens nor the register; the per-task full gate is
  expected green *with the pre-existing GAP rows standing*; Task 12 batches all matrix,
  register and requirements changes into a single human-applied change, verified by one
  `./init.sh` run.
- **New enforcement modules join `BUILTIN_PROTECTED_PATHS` in the same change that ships
  them** — the 2026-08-22 precedent (an editable gate is a disableable gate). Applies to
  `ingress.py`, `classifier.py`, `review.py`, and `semantic-model.lock.json`. Since the
  list lives in `permission.py`, this is itself part of the Task 12 human batch.
- Baseline gate: `./init.sh` in the unfilled template exits 1 with the same 5-error set;
  gate on the error set, never on exit 0 or warning count.
- Markdown table cells carry no literal pipe characters.
- pytest may run a test file; no test may require it to pass (`__main__` fallback).

## 6. Acceptance conditions

Original §6 items 1–15 stand, with one rebinding: item 13's "accepted demo" refers, in
this tree, to **the template's own `demo/` suite and shipped examples remaining green
with their recorded evidence unchanged** — the fork's seven-phase demo and its
`evaluation/security-in-action/` do not exist here. Add:

16. No second implementation of any action-gate rule exists (AD-7), proven the way this
    repo already proves it: an **anti-drift test** that scans the semantic-layer modules'
    source for `re.compile` and for any import path that bypasses the owner modules
    (`content_trust.scan_text`, `permission.make_permission_check`), plus reviewer
    attestation that no policy predicate is re-derived — grep proves the mechanical half;
    the reviewer owns the semantic half, and this condition says so rather than
    overclaiming.
17. R-1, R-2 and R-3 are stated in the profile and the verdict, with the classifier-
    false-negative replay case green.
18. The AD-8 dependency exception is recorded and human-approved before any classifier
    artifact enters the tree.
19. Every new enforcement module ships inside `BUILTIN_PROTECTED_PATHS` (§5), and a test
    pins each addition the way `tests/test_protected_paths.py` pins the existing twelve.
