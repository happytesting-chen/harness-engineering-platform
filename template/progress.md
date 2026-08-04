# Progress — Security-kit enhancement (security-tailor)

> NOTE: this is the planning-with-files session log for the DESIGN work, distinct from
> `Harness-Best-Practice/progress.md` (the template's own runtime journal).

## Session 1 — 2026-08-04

### Done
- Explored template + Security-kit end to end (see findings.md).
- Brainstormed via superpowers:brainstorming. Locked decisions:
  - Core job: tailor controls to the product (reasoning → SKILL, not hook).
  - Triggers: init + on-demand + phase sign-off.
  - Output rigor: checkable artifact (coverage.json) gated by init.sh.
  - Scope: applicability + gaps ONLY (no new controls, no policy diffs, no verify authoring).
- Answered the "binding / add-omit / standalone" question grounded in install.sh + init.sh.
- Chose **Approach A**. Wrote spec:
  `docs/superpowers/specs/2026-08-04-security-tailor-design.md`.
- **Rev 2:** extended to **layer D (dev-time steering)** per user ("Extend to dev-time
  steering"). Confirms 3 active layers: B selection, C coverage gate, D steering.

### Spec covers (per request)
context · triggers · implementation (5 pieces) · eval · advice · open questions.

### The five new pieces (start small)
1. `security-tailor` skill (.claude/commands + kiro/steering mirror)
2. `Security-kit/coverage.json` (machine-readable verdict, Context/-hashed)
3. `Security-kit/check_coverage.py` (fail-closed init.sh gate)
4. `tests/test_coverage.py` (ground-truth)
5. `Security-kit/active-controls.md` (**layer D** — tailored steering, loaded via
   `@import` in CLAUDE.md + `inclusion: auto` Kiro mirror; NOT `.claude/rules/`)
Plus wiring: init.sh block 5b, /init-project step 2b, /session-cycle sign-off,
CLAUDE.md import, install.sh TIER1 + 2× sed (add/omit), SECURITY-MANIFEST.md tiers.

### Verified against real files (2026-08-04, rev-2 self-review)
- CLAUDE.md:9 uses `@Harness-Best-Practice/AGENTS.md` import → layer-D load path proven.
- kiro/steering/security.md:1-2 uses `inclusion: auto` → Kiro mirror path proven.
- SECURITY-MANIFEST.md:84 holds the 16/24 vs 24/24 A/B numbers.
- example is lowercase `examples/claims-agent/context/`; eval report lives at
  `examples/claims-agent/evaluation/TEMPLATE-EVALUATION-REPORT.md` (fixed stale paths).

### Next
- AWAITING user review of the rev-2 spec (layer D + §8 open questions).
- On approval → superpowers:writing-plans to produce the implementation plan.

### Open questions (spec §8)
1. Context hash scope (proposal: all non-template .md, sorted+concatenated).
2. coverage.json location (proposal: Security-kit/).
3. Granularity: per-OWASP-id (20, proposed) vs per-SECURITY.md-control (40).
