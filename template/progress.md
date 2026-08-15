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
  `docs/superpowers/specs/archive/2026-08-04-security-tailor-design.md` (archived 2026-08-13;
  superseded by `2026-08-13-security-kit-build-design.md`).
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

---

## Sessions 2–8 — 2026-08-05 → 08-14 (reconstructed from git, not from a log)

**This log had an 11-day gap.** It stopped at 2026-08-04 while the work continued through
2026-08-14; the entries below are recovered from `git log -- template/` and are commit subjects
plus what the spec records, **not** a contemporaneous account. Treat the arc as reliable and any
detail not carried by a commit message or a spec section as absent rather than remembered.

| Date | Commit | What landed |
|---|---|---|
| 08-05 | `3e09240` | Phase-A design spec — deployed tool-mediation gate (runtime, post-build) |
| 08-07 | `a9332f9` | **Gate 1b** — protect the mechanism from its own agent (S2.4) |
| 08-08 | `70a12a1` | Gate 1a re-done to match protected paths **by file identity**, fail closed on bad policy |
| 08-08 | `3d64fac`, `a7e3c81` | eval: missing `recorded/` prints guidance, not a traceback; gate count corrected in prose |
| 08-11 | `c80b3b1` → `0fdcb11` | mechanism-inventory spec, then **three specs reconciled into one build order**; rev 2 re-measured against a clean HEAD; **a defect claim withdrawn because measuring disproved it** |
| 08-11 | `f11a182`, `f16525a` | the measured control matrix lands; **S2.4's shell gate covered 43% of what `SECURITY.md` claimed** — measured, then said so |
| 08-12 | `36fba08`, `223b1f6` | conceptual design cross-checked against the code; the secret scanner **could not see its own input** |
| 08-14 | `941dc49` | build-design doc improvements; CI workflow asserting the §7.4.1 BASELINE |

The through-line worth carrying forward: every one of those security commits is phrased as *a
measurement that contradicted a claim the docs already made*. That is the pattern §1.6 asks for,
and it is the reason the spec is trustworthy where it is specific.

---

## Session 9 — 2026-08-15

Two threads: close the last open deny-list defect, then produce the first drafter recall number.

### Done — item 11, the per-command deny-list defect (`5f95a4d`, committed)

`[^|;&]` in four `deny-list.json` regexes excludes `;` `|` `&` but **not `\n`**, so tokens from two
different commands compose into a match neither earns alone — `sed -n '1,10p' <path>` newline-joined
with `grep -n 'gate' <path>` was **denied**, while the same pair joined by `; ` was **allowed**. The
asymmetry is what made it a defect rather than a policy choice.

Fixed with `_shell_lines()` in `permission.py` (now **427 lines**) — split on newlines, then match
each command line separately. Two cases where a newline does *not* end a command, and both are
bypasses if missed: backslash-continuation (unfolded first) and a newline **inside quotes**
(tracked). An unterminated quote yields one unsplit line — fail closed.

Measured 4 implementations × 5 cases before shipping:

| implementation | wrong |
|---|---|
| shipped (`[^\|;&]`, whole blob) | 2 — both **over**-block |
| naive `[^\|;&\n]` | 2 — both real attacks **allowed** |
| plain per-line split | 1 — backslash-continuation attack allowed |
| unfold-then-split (**the spec's own recommended fix**) | 1 — quoted-newline attack allowed |
| `_shell_lines()` (quote-tracking) | **0** |

That table corrected two errors in the spec's own four-case version: it had credited a plain
per-line split with a DENY it does not produce, and it omitted the quoted-newline case — which
concealed that the fix the spec recommended was itself insufficient.

**Shipped as a patch, not an edit.** `permission.py` is in `BUILTIN_PROTECTED_PATHS`, so Gate 1a
refused its own author — exit 2, `protected path (S2.4)`. The mechanism worked on the person fixing
the mechanism. `item11-per-command-denylist.patch` is still in the tree and is now redundant;
delete it or keep it as the provenance record, but decide.

§4 of `tests/test_shipped_policy.py` was a **pin** asserting the defect; it is now the regression
suite for the fix, with named BYPASS GUARD cases for both newline-that-isn't-a-separator forms.

**Baseline unchanged: `exit 1, 5 error(s)`** — the pin flipping fail→pass cancels the new error, so
the count is coincidentally identical. I predicted 4 and was wrong; measured three runs each way.

### Done — first drafter recall measurement (§5.1a task 5)

`/security-tailor` takes **no path argument** (`Context/` is named at 8 sites in the command;
`check_coverage.py:20` hardcodes `CONTEXT_DIR`), so `eval/README.md`'s instruction to run it
"against `corpus/<case>/context/`" described a capability the template does not have. Corrected to
swap-and-revert: copy a case's `product.md` into `Context/`, run, record, **revert**.

```
cases=2  TP=33 FP=0 FN=2 TN=5
recall=0.943  precision=1.000
```

`rag-product` **excluded as contaminated** — its `labels.json` had been read in the same session
that did the classifying. Declared rather than scored, because the contamination is invisible in
the output: the recall figure looks identical either way.

Both FNs are in `claims-agent` and are **one error**: `n_a` asserted from a structural absence that
does not remove the property the id names.
- **ASI03** — "on-prem, no external API calls" removes cloud IAM, not *privilege*. The agent writes
  a terminal APPROVED/REJECTED decision; crosswalk:80 puts the mechanism at Gate 2, which is local.
- **ASI08** — read as topology-dependent. Crosswalk:85 defines it as a **sequence** property
  (*"nothing bounds a run"*) and crosswalk:117-118 files it under "the sequence / the run". A single
  agent has runs.

**Read precision with suspicion.** `n_a` was predicted only 7 times in 40, so there was almost no
opportunity to be wrong in the negative direction. 9 of 35 positive predictions were `gap` and
**all 9 were correct** — the "never guess ⇒ gap" rule (`security-tailor.md:22`) is carrying the
recall number, exactly as §1.8.12 predicts. Recall is the signal; precision here is an artifact.

Not exercised, and recorded so the figure is not read as broader than it is: `check_coverage.py`
Rule 3 and the layer-D `active-controls.md` rule. Every `applies` mapped to an **existing** `SEC-*`
row per the drafter's own guardrail, and `active-controls.md` was deliberately not regenerated.
`--stamp` ran on both cases, so the freshness path did execute end to end.

Two mappings were corrected mid-run **by the checker's own rule**, which is the gate working on the
drafter: `SEC-XXX-001` is the `{{PROJECT_SPECIFIC_…}}` stub row that `PLACEHOLDER_RE`
(`check_coverage.py:87`) would have errored on, and three ids were mapped to `*-GAP-001` rows whose
verification cell is literally `none` — under `security-tailor.md:21` those are `gap`, not `applies`.

### Figures corrected this session

`permission.py` 388 → **427** · doorway block `:334-388` → `:373-427` · all six §4.2.6 line refs ·
`7-line stub` → **6-line** · test count **62 → 61** (`git show HEAD` proves the file went 6 → 7
tests, so the +1 delta was right and both totals were off by one; per-file now recorded in §2).

### Next

1. **Item 16** — the `progress.md` staleness warning compares filesystem mtimes and **git does not
   record mtimes**, so on a fresh checkout it reports "up to date" unconditionally: a check that
   cannot fail when it should. §7.4.1's honest options are drop it, or take recency from
   `git log -1 --format=%ct`. Currently **Unowned**. This is the only genuine defect in the
   `./init.sh` output.
2. **§5.1a task 4** — `kiro/steering/active-controls.md` mirror + the two `check_coverage.py`
   constants, shipped together (§4.6.4). Last open *template* task.
3. **One-line `security-tailor.md` edit** — "before recording `n_a`, read that id's crosswalk row;
   several ids are sequence or privilege properties that survive a simple topology." Would have
   caught both recall misses. `:20` says "Cite what rules it out" but never says where to read it.
4. Re-run `rag-product` in a **fresh session** to get the third case honestly.
5. Decide on `--context <dir>`: cheap now, a patch after §5.5 adds `check_coverage.py` to
   `BUILTIN_PROTECTED_PATHS`. Deliberately deferred until a recall figure existed — it now does.
6. Delete or keep `item11-per-command-denylist.patch`.

### Unresolved

A one-off `✗ E2E tests FAILED` on a fresh scratch tree, never reproduced across ~9 later runs.
Cause unknown. Flagged because **CI runs cold every time**, which is exactly the condition that
produced it.

### Decisions

| Date | Decision | Rationale |
|---|---|---|
| 08-15 | Deny-list matches **per command line**, with quote and continuation tracking | The `;`-vs-newline asymmetry was a measurable defect; the two naive fixes each trade a false positive for a real bypass |
| 08-15 | Eval reaches the drafter by **swap-and-revert**, not a path flag | No path parameter exists; a flag is a design decision that should be spent *after* a recall figure, and recall is now known |
| 08-15 | Reverting `Context/` and deleting `coverage.json` is **mandatory**, not tidiness | Leaving either clears two errors §7.4.1 asserts are present |
| 08-15 | `rag-product` declared contaminated, not scored | Label exposure is invisible in the output, so the only defence is disclosure |
| 08-15 | Ship policy fixes to protected paths as **patches** | Gate 1a denies the author; that is the control working, not an obstacle to route around |
