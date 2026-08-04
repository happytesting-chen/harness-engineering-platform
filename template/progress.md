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

### Rev 3 — audit + SAST eval (2026-08-04)
- **Read install.sh + init.sh + SECURITY-MANIFEST.md in full.** Found 3 no-security leaks
  in rev-2 §5.2 and fixed them in-spec:
  - TIER1 deletes whole DIRS (install.sh:62-66), so per-file Security-kit/tests entries
    were redundant. `.claude/commands/security-tailor.md` was NOT covered → would dangle.
  - install.sh never edits CLAUDE.md today → the @import strip my rev-2 promised didn't
    exist. Two genuinely-new install.sh actions now specced (rm command file + sed CLAUDE.md).
  - block-5b additions self-skip via `if [ -d governance ]` → the init.sh strip is unneeded.
- **User pushed: eval must be SAST-like to prove effectiveness.** Chose Q1+Q2:
  - Q1 selection benchmark — labeled product corpus + confusion matrix; headline = tailor
    RECALL (false n_a = missed control = false negative). Replaces anecdotal false-N/A audit.
  - Q2 NEW component `Security-kit/sast_scan.py` — heuristic stdlib AST+regex static scan of
    product tools/prompts for the sinks of SELECTED controls; benchmarked on planted-vuln
    corpus (detection rate). Honest boundary: heuristic, NOT taint-complete.
  - claims-agent has NO product .py to scan (tools/ = md+json only); its live check is
    wildcard mcp-allowlist scope (ASI04). Planted-vuln corpus is the scanner's real proving
    ground. Verified 2026-08-04.
- Tailor = threat-modeling/control-selection (NOT SAST). sast_scan = SAST-the-capability
  (heuristic). Methodology (corpus+matrix) borrowed from SAST for BOTH.

### Next
- AWAITING user review of the rev-3 spec (§4.6 scanner, §6 benchmark rewrite, §5.2 audit fixes).
- Still open: §8 questions (hash scope, coverage.json loc, granularity).
- On approval → superpowers:writing-plans to produce the implementation plan.

### Open questions (spec §8)
1. Context hash scope (proposal: all non-template .md, sorted+concatenated).
2. coverage.json location (proposal: Security-kit/).
3. Granularity: per-OWASP-id (20, proposed) vs per-SECURITY.md-control (40).
