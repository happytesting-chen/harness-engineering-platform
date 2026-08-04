# Progress Log — Build B design artifacts

> Planning-with-files session log. Separate from `Harness-Best-Practice/progress.md`
> (the build journal). This file tracks the DESIGN task only.

## Session 1 — 2026-08-04

### Done
- [x] Restored context: no prior planning files; Build A signed off; core verified live.
- [x] Confirmed seam probe results (5 cases) → findings.md.
- [x] Created task_plan.md, findings.md, progress.md.

- [x] BLOCKER found + logged: contract bans LLM for A+B (`claims-architecture.md:36`). Reframed as Build C proposal.
- [x] Phase 2: `Context/ai-stack.md.proposed` (credential ranking, seam, coverage-from-policy).
- [x] Phase 3: `Context/deployment.md.proposed` (PII-boundary decision, egress, content-trust boundary).
- [x] Phase 4: `evaluation/BUILD-C-PHASE-PROPOSAL.md` (phase entry + acceptance criteria + eval payoff table).
- [x] Corrected stale template paths (`security/`→`Security-kit/`, `tools/`→`governance/`) in drafts.

### Deliverables (all `.proposed` / proposal — nothing live, nothing signed)
- Context/ai-stack.md.proposed
- Context/deployment.md.proposed
- evaluation/BUILD-C-PHASE-PROPOSAL.md

### Session 2 — GREENLIT + scaffolded (2026-08-04)
- [x] Human "yes" + decisions: Bedrock IAM-role / minimal SDK / small-fast model.
- [x] Amended contract (Build C clause); promoted ai-stack.md + deployment.md live; added phase-04 active.
- [x] Verified: 38 passed, hooks 10/10 (gate reopened), init.sh exit 0, egress still [], claims/ still stdlib-only.

### Session 3 — STUB extractor built + seam proven (2026-08-04)
- [x] Built `extraction/` (in-phase, no egress/creds/compliance — model is FAKE): `__init__.py`,
      `model.py` (Extractor protocol + FakeExtractor + BedrockExtractor-that-raises),
      `policy_store.py` (trusted coverage lookup, synthetic SYN-*), `service.py` (process_email).
- [x] `extraction/tests/test_extraction.py` — 12 cases, all pass.
- [x] **Case-5 lie DEFEATED runnably:** FakeExtractor proposes covered==submitted (480/480) on
      SYN-CLAIM-102 whose trusted policy = 10.00 → REJECTED/COVERAGE_SHORTFALL. service.py sources
      covered_amount from policy store, not email. The LLM cannot move a number it does not control.
- [x] Verified: 50 passed (tests+claims/tests+extraction/tests); claims/ untouched & stdlib-only;
      extraction/ imports no boto3/network (grep clean); egress still []; init.sh exit 0.
- Design refinement: service.py copies proposal + overrides only coverage (does NOT whitelist-filter),
  so a hallucinated field is caught by unchanged validate() as UNKNOWN_FIELD — honest defense, not silent drop.

### Next (first task INSIDE phase-04 — gated)
- [ ] **Compliance/data-processing review** (PII → Bedrock) — HARD PREREQUISITE, blocks all below.
- [ ] After review: add one Bedrock host to egress_hosts; add `claims_extractor` tool (gated_until phase-04).
- [ ] Swap FakeExtractor → real `BedrockExtractor` (Bedrock small/fast, structured JSON to validate.py's fields);
      coverage stays from policy lookup. Seam + policy override already proven by the stub, so this is a client swap.
- [ ] Labeled email→record oracle fixtures; run eval (cost N/A→real, reproducibility measured).

### Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| (none yet) | — | — |

### Notes
- Drafts only — no code, no key, no egress change, no phase self-transition.
- Will present all three for human review before anything is finalized into a live phase.
