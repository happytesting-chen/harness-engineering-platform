# Progress

## Current State

- **Last updated:** 2026-08-04 (session 4)
- **Active phase:** **phase-04 — Build C (LLM extraction)** → `active` (opened by human "yes" + signed Build C amendment). phase-01/02/03 PASSING.
- **Session number:** 4
- **Gate note:** opening phase-04 active RESOLVED the prior "no active phase" fail-closed — the 2 expected test_hooks failures now pass (10/10). Gate reopened correctly.

## Done

### Session 1 — init
- [x] Copied template into `claims-build/` and imported claims context into `Context/`
- [x] Filled all harness placeholders (CLAUDE.md, AGENTS.md, feature_list.json, mcp-allowlist.json, deny-list.json)
- [x] Filled `Security-kit/control-matrix.md` — 5 rows, one per trust boundary
- [x] Added `init.sh` check (e): hook-path integrity (catches broken hook path vs. real policy BLOCK)

### Session 2 — phase-01 sign-off + phase-02 implementation
- [x] phase-01 → `passing` (human sign-off recorded), phase-02 → `active` in feature_list.json
- [x] Built stdlib-only `claims/` package: validate → normalize (exact Decimal) → route (sole authority) → fail-closed one-minimal-write
- [x] Added 5 synthetic `SYN-*` fixtures (approved / rejected / untrusted / malformed / safety-flagged) + 14 tests
- [x] Verified stdlib-only: no network/provider/subprocess imports in `claims/`
- [x] **phase-02 verification passes:** `./init.sh && python3 -m pytest tests claims/tests -v` → exit 0, 33 passed

### Session 2 (cont.) — review + Fix #1 (bind the gated tool to real code)
- [x] Review reconciliation (read-only): confirmed build copy location, filled files, gaps, over-engineering. Key gap found: `claims_runner` was an allowlist token bound to NO executable — gate proven only on the generic `exploit_runner`, not on claims.
- [x] **Fix #1a:** added `claims/runner.py` — the real `claims_runner` entrypoint (CLI: read one fixture → pipeline → one minimal fail-closed write). +5 runner tests.
- [x] **Fix #1b:** added `demo/claims_demo.py` — gate now DENIES `claims_runner` while phase-01 unsigned, ALLOWS after sign-off, and the ALLOW runs the REAL runner (APPROVED on SYN-FIXTURE-001). Generic `demo/demo.py` left intact.
- [x] Re-verified: `./init.sh && pytest` → exit 0, **38 passed** (was 33). Demo restores policy files intact. `--nogate` shows fail-closed writer still refuses duplicate = real defense-in-depth.

### Session 3 — phase-02 sign-off + phase-03 evaluation & snapshot
- [x] Human sign-off recorded for phase-02; routing rule confirmed. phase-02 → `passing`, phase-03 → `active`.
- [x] **phase-03 fresh-session evaluation** (read/run-only, no new features):
  - Verification rerun: `./init.sh` exit 0; `pytest tests claims/tests -q` → 38 passed, exit 0.
  - Correctness: real `claims.runner` over 5 SYN fixtures → all 3 terminals reached.
  - Traceability: 5/5 actual == fixture oracle; gate DENY→ALLOW over the REAL `claims_runner` (demo).
  - Reproducibility: byte-identical result sha256 across fresh boundaries; duplicate write refused (exit 2).
  - Isolation: stdlib-only guard clean.
- [x] Wrote human-reviewable snapshot: `evaluation/build-a/SNAPSHOT.md` (PROPOSED). No self-transition.
- [x] **Generalized eval into a template primitive** (per user request — demonstrate effectiveness/cost/accuracy):
  - `evaluation/eval.py` — generic `evaluate(cases, decide_fn, oracle_key, repeats, usage_fn)`; measures accuracy/reproducibility/latency (real) + cost (N/A until a real provider is wired — never fabricated). Reference target = the project's own gate over `tests/fixtures.json` (zero deps).
  - `evaluation/SNAPSHOT.template.md` + `evaluation/README.md` (how to swap in a real `task_fn`/`usage_fn`; the oracle rule).
  - Proven generic: also evaluated `claims.pipeline.decide` over SYN fixtures → 100%/100%.
  - Wired: `init.sh` non-fatal eval check; `AGENTS.md` verify line; build-a snapshot regenerated.
  - **Ported to canonical template** (`evaluation/` + BEST-PRACTICES rows + init.sh check + AGENTS.md tree + init-project skill guidance + feature_list `_recommended_final_phase`).

### Session 4 — Build C opened (LLM extraction) — GOVERNANCE SCAFFOLDING ONLY
- [x] Human "yes" to amend the LLM ban. Decisions via AskUserQuestion: **Bedrock (cloud IAM role)** · **minimal raw SDK** · **small/fast model**. PII crosses boundary → compliance review required.
- [x] Amended `Context/claims-architecture.md` Prohibited Effects with a scoped **Build C amendment** (LLM = extraction only; router stays sole authority; IAM role not static key; one Bedrock host; coverage-from-policy-not-email; content_trust screens prompt input; A/B stay deterministic).
- [x] Promoted Context drafts to live: `Context/ai-stack.md` + `Context/deployment.md` (filled with the 3 decisions; removed the `.proposed` copies).
- [x] Added `phase-04` (Build C) to `feature_list.json` as `status: active`, sign-off + gating-prerequisite recorded.
- [x] Verified: full suite 38 passed; test_hooks 10/10 (gate reopened); `./init.sh` exit 0 (PASS, 1 warning); **egress_hosts still [] ; claims/ still stdlib-only** (no LLM code/creds/egress opened this session).
- Planning artifacts: `task_plan.md`, `findings.md`, root `progress.md`; `evaluation/BUILD-C-PHASE-PROPOSAL.md` retained as the phase's acceptance-criteria reference.

### Session 4 (cont.) — retarget demo + eval to the claims domain (docs/wiring only)
- [x] **eval.py retargeted:** reference wiring swapped from the *permission gate* (`_gate_decide_fn` over `tests/fixtures.json`) to the *deterministic claims engine* (`_claims_decide_fn` → `claims.decide` over `claims/tests/fixtures/*.json`). "Accuracy" now means claims-decision accuracy. `evaluate()` kept generic — only the reference wiring + target string changed.
  - Oracle isolation preserved: each case is `{"record", "oracle"}`; `decide_fn` reads only `record` (the fixture MINUS its `expected` block), so the oracle never reaches the decision path. `_oracle_string()` normalizes to `OUTCOME/REASON_CODE`.
  - Result: **100% accuracy (5/5), 100% reproducibility, cost N/A** (no provider wired — never fabricated). Exit 0.
- [x] **Docs pointed at `claims_demo.py`:** `AGENTS.md` "How to Run" + `README.md` demo block now invoke `demo/claims_demo.py` (gate governs the REAL `claims_runner`); `demo/demo.py` explicitly labeled the generic pentest illustration, kept as a template reference (per human "keep both" decision).
  - `evaluation/README.md` honesty-rule + reference-target prose retargeted to `claims.decide`. `SNAPSHOT.template.md` stale "(FakeModel/gate) wiring" → "(deterministic, no-provider) wiring"; `evaluation/build-a/SNAPSHOT.md` regenerated (measured, not hand-edited).
- [x] Verified: `./init.sh` exit 0 (PASS, 1 warning); `pytest -q` → **50 passed**; `claims_demo.py` gate mode shows bash ✓ → claims_runner ⛔ DENIED (phase-01 unsigned) → ✓ ALLOW after sign-off; `--nogate` runs claims_runner immediately (fail-closed writer still refuses the duplicate = defense-in-depth). **egress_hosts still []; claims/ untouched.**
- Scope note: docs/eval-wiring only — no claims/ logic, no provider, no egress, no phase self-transition.

## In Progress

- **Current task:** none — phase-03 signed off. Next work (security phase) not yet scoped.
- **Blockers:** none functional.
- **⚠ Known expected state — gate intentionally closed:** all three phases are now
  `passing`, so there is **no `active` phase**. `permission.py` fails closed
  (`no active phase — cannot determine tool permissions`), which denies `bash`/`write_file`.
  Consequence: `tests/test_hooks.py` has 2 expected failures (`test_pascalcase_bash_allowed`,
  `test_pascalcase_write_allowed`) and `./init.sh` exits 1. This is the gate correctly
  refusing an undefined state — **not corruption**. It resolves the moment the next
  (security) phase is added with `status: active`. Per human decision 2026-08-04, we
  leave the gate closed until that phase is scoped (did not fabricate a placeholder phase).
- **Canonical-template finding (fixed there, not here):** signing off the *final* phase
  bricks any project's gate. Hardened `permission.py` in the canonical template to treat
  "all phases passing" as steady-state (see template commit). claims-build deliberately
  keeps the strict fail-closed behavior for now.

## Next Steps

1. ✅ **phase-03 signed off** (human, 2026-08-04) — evaluation primitive committed to canonical template (`1d64222`), snapshot PROPOSED and accepted.
2. **Security phase** (next active): install Security-kit via `install.sh --no-security` **on a copy** for the A/B comparison; reconcile Fix #2 (content-trust matrix redundancy). Requires a new phase entry in `feature_list.json` when scoped.

## Deferred / Backlog (agreed, not done this phase)

- **Security-kit omitted this phase (deliberate).** Next phase: install Security-kit and A/B what the AI-security layer (content-trust injection screening, secret-scan hook, audit) catches that the bare gate does not. Use `install.sh --no-security` **on a copy** — do NOT hand-delete (settings.json wires `Security-kit/secret_scan.py`; check (e) hard-fails if it vanishes while wired).
- **Fix #2 (content-trust redundancy) deferred to the security phase.** control-matrix cites `Security-kit/content_trust.py` for the untrusted-fixture boundary, but THIS phase enforces that boundary in `claims/validate.py` (the `expected` oracle never reaches `decide()`; proven by `test_expected_block_does_not_influence_decision`). Reconcile the matrix when content_trust.py is actually installed.
- **Routing rule needs human confirmation.** Terminal *definitions* come from Context/; the *thresholds* (covered<submitted→REJECTED, covered>submitted→PENDING_REVIEW, exact→APPROVED) are an inference, recorded below. Confirm this is the intended Build A rule.
- **Template drift (cosmetic):** build copy predates canonical `security/`→`Security-kit/` rename; some copied files still say `security/` internally. Out of init.sh gate scope. Re-copy from canonical template if a faithful snapshot is needed.
- **Unfilled `{{...}}` stubs** in `.claude/commands/domain-workflow.md`, `kiro/steering/domain-workflow.md`, `kiro/hooks/governance-check.json` — outside init.sh's 5-file placeholder scope, so they pass silently. Fill only if the Kiro runtime is used.
- **init.sh line ~264 cosmetic bug** (found phase-03): Q5 fresh-session check prints `[: integer expression expected` — a count returns two lines, so the integer test sees `0\n0`. Non-fatal; Q5 and overall run still PASS (exit 0). Belongs to a maintenance fix (and should mirror to the canonical template), NOT phase-03. Deferred to avoid touching code during an evaluation-only phase.

## Decisions Made

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-08-04 | Context source = reuse existing claims context docs | Avoid re-deriving a product definition already written |
| 2026-08-04 | Build in a fresh copy (`claims-build/`), not in-place | Keep the canonical `template/` clean while dogfooding |
| 2026-08-04 | `claims_runner` gated_until phase-01; `egress_hosts: []` | Claims contract forbids network/provider/cloud; default-deny egress |
| 2026-08-04 | Added hook-path integrity check to init.sh (mirrored to canonical template) | A missing hook script exits 2 exactly like a policy BLOCK — self-guarding deadlock; check surfaces the config error distinctly |
| 2026-08-04 | Router is sole decision authority; validation defects → PENDING_REVIEW (never REJECTED) | Contract: no permissive fallback; malformed/unknown/untrusted is a review case, not a business rejection |
| 2026-08-04 | Reviewed Build A rule: untrusted/safety/incomplete-doc → PENDING_REVIEW; covered<submitted → REJECTED; covered>submitted → PENDING_REVIEW; covered==submitted → APPROVED | Reaches all three terminals; trust/safety gates precede monetary math |
| 2026-08-04 | Money as exact `Decimal` from 2-fraction-digit strings; floats rejected in validation | Contract requires exact monetary comparison, not binary-float approximation |
| 2026-08-04 | Writer uses exclusive-create + boundary resolve check | One minimal write; duplicate/out-of-bound/unattributable writes fail closed |

## Notes for Next Session

- phase-02 evidence: `./init.sh && python3 -m pytest tests claims/tests -v` → exit 0, 33 passed (19 retained core + 14 claims). Retained core tests unchanged.
- `expected` in fixtures is an oracle only — asserted in tests, never fed to `decide()` (proven by `test_expected_block_does_not_influence_decision`).
- Determinism proven: repeated `decide()` equal; written results byte-identical across runs.
- Keep `progress.md` current — init.sh warns (not errors) when it lags code edits.
- Clean state: `__pycache__` / `.pytest_cache` purged before handoff.

---

## Session Handoff (fill only when ending mid-task)

> phase-04 (Build C — LLM extraction front-end) is ACTIVE. The STUB extractor is built and the
> seam is proven runnably (50 tests pass, init.sh exit 0). No egress/creds/compliance were needed
> because the model is a FakeExtractor.
>
> **State:** `extraction/` module complete — model.py (Extractor protocol, FakeExtractor,
> fail-closed BedrockExtractor), policy_store.py (trusted coverage, synthetic SYN-*), service.py
> (process_email: extract → override coverage from policy → unchanged decide()), and 12 passing
> tests including the case-5 lie proof (covered==submitted lie on a shortfall claim → REJECTED via
> policy override). claims/ untouched & stdlib-only; egress_hosts still []; router still sole authority.
>
> **Parked at the human gate.** Everything remaining in phase-04 is GATED: it needs a
> compliance/data-processing review (PII crosses to Bedrock) + explicit egress authorization before
> ANY real provider call. Do NOT open egress, add a Bedrock host, register the claims_extractor tool,
> or build the real BedrockExtractor without that human sign-off. The stub proves the mechanism; the
> real client is a swap behind the gate.
>
> **Flagged (pre-existing, not fixed — out of scope):** init.sh:274-276 emits a cosmetic
> "integer expression expected" warning (grep -c zero-match + `|| echo "0"` yields `0\n0`). Exit still 0.
