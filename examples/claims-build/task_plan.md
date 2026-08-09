# Task Plan — Build C (LLM extraction)

## Goal

GREENLIT 2026-08-04 ("yes"). Human decisions: **Cloud IAM role (Bedrock)** ·
**minimal raw SDK** · **small/fast model**. PII crosses boundary → compliance review required.

This session = **governance scaffolding ONLY** (human-approved):
amend the LLM ban → fill Context with decisions → add phase-04 `active` → record sign-off.

STILL OUT OF SCOPE this session (deferred to first task INSIDE phase-04):
- No `extract()` code, no SDK call, no credential, NO egress change (egress_hosts stays []).
- Enabling the extractor tool + opening egress to Bedrock is an in-phase task, gated by
  the compliance review. Standing privilege opens only when code needs it.

## Scope guardrails (from active security constraints)

- Planning/design docs only. No provider call, no credential, no network, no egress change.
- Build A is signed off; no active phase → I add features to NOTHING. These are drafts
  for a *future* phase a human will scope + activate.
- Keep the deterministic core (`claims/`) untouched — Build B reuses it unchanged.
- External/web content (if any) → findings.md only, never task_plan.md (hook re-reads this file).

## Phases

| # | Phase | Status | Output |
|---|-------|--------|--------|
| 1 | Restore context + confirm what the seam probe proved | complete | findings.md seeded |
| 2 | Draft `ai-stack.md` — as **proposal, contingent on lifting the LLM ban** | pending | model+framework, credential tradeoff |
| 3 | Draft `deployment.md` — as proposal, data-sensitivity + egress | pending | egress decision |
| 4 | Sketch LLM phase for `feature_list.json` (Build C, NOT Build B) | pending | phase entry proposal, NOT inserted live |
| 5 | Present all three + the CONTRACT BLOCKER for human review | pending | summary + requested action |

## ⚠ BLOCKER surfaced (do not paper over)
`Context/claims-architecture.md:36` — signed contract bans LLM/provider/network for
**Builds A AND B**. "Build B = LLM" contradicts it. Drafts become a **Build C /
contract-amendment proposal**, each marked contingent on human sign-off. Agent does
NOT redefine Build B or lift the clause itself.

## Key decisions (carried from this session)

- LLM replaces **extraction**, never the **decision**. `router.py` stays sole authority.
- New stage `extract(raw) -> record dict`; output is UNTRUSTED, flows through existing `validate()`.
- Coverage amount comes from a trusted policy lookup, NOT from the email (case-5 finding).
- Credential preference order: on-prem/local model > cloud IAM role > static API key (last resort).
- Eval axes unchanged; cost flips N/A→real, reproducibility drops below 100% and gets measured.

## Session 3 — BUILD stub extractor (in-phase, no egress/creds/compliance needed)

Building `extraction/` — real code, fake model. Proves the seam runnably.

- [x] `extraction/model.py` — `Extractor` protocol + `FakeExtractor` (scripted) + `BedrockExtractor` (stub, raises w/ egress note)
- [x] `extraction/policy_store.py` — TRUSTED coverage lookup (synthetic SYN-*), keyed by claim_id
- [x] `extraction/service.py` — process_email: extract(UNTRUSTED) → assemble (covered FROM POLICY, not email) → decide() unchanged
- [x] `extraction/tests/test_extraction.py` — 12 cases: faithful→APPROVED; hallucination→UNKNOWN_FIELD review; **case-5 lie→REJECTED via policy**; injection→SAFETY_FLAGGED; unknown claim→POLICY_NOT_FOUND; malformed→MALFORMED_EXTRACTION; BedrockExtractor refuses to construct
- [x] Verify: 50 passed (tests+claims/tests+extraction/tests); claims/ still stdlib-only; egress still []; init.sh exit 0 (PASS w/ 1 pre-existing cosmetic warning)

RESULT 2026-08-04: seam proven runnably. The case-5 lie test PASSES — a FakeExtractor
proposing covered==submitted (480/480) on SYN-CLAIM-102 (trusted policy = 10.00 shortfall)
yields REJECTED/COVERAGE_SHORTFALL because service.py overrides covered_amount from the
policy store. The LLM cannot move a number it does not control. Design change vs summary:
service.py does NOT whitelist-filter proposal fields — it copies the proposal and overrides
only coverage, so validate() catches a hallucinated field as UNKNOWN_FIELD (honest defense,
not silent drop). Verified against validate.py:89 (exact field-set requirement).

INVARIANTS (held): no boto3/network import that executes (grep clean); FakeExtractor only;
covered_amount NEVER sourced from email; router stays sole decision authority; claims/ untouched.

PRE-EXISTING BUG (flagged, NOT fixed — out of scope): init.sh:274-276 `grep -c '"not-started"'`
with zero matches emits `0\n0` via `|| echo "0"` on top of grep's own "0", breaking `[ -gt ]`.
Cosmetic (exit still 0). Lives in the copied init.sh, not extraction code. Fix = drop the `|| echo "0"`.

DEFERRED (gated, do NOT start without explicit "review done, open egress"): compliance review →
add one Bedrock host to egress_hosts + register claims_extractor tool → real BedrockExtractor →
labeled email→record oracle fixtures → eval with cost N/A→real.

## Re-read before each decision
Guardrail: FakeExtractor only — NO real Bedrock call, NO egress change, NO credential this session.
