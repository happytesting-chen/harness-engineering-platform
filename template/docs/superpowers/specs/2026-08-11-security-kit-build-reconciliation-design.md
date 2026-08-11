# Security-Kit Build Reconciliation — Design Spec

> **Purpose.** Three design specs describe the Security-Kit. They overlap on six shipped
> files and contradict each other in seven measurable places. This spec resolves the
> contradictions, assigns one owner per shared file, and gives one ordered build sequence.
> It adds **no** new mechanism and **no** new enforcement of its own.
>
> **Status:** rev 1 · 2026-08-11 · all cross-claims below were measured against the tree on
> 2026-08-11, not recalled.

**Scope of authority.** Each source spec remains authoritative for its own domain. This
document is authoritative for exactly three things: (1) the seam resolutions in §2, (2) the
shared-file ownership table in §3, (3) the build order in §4. Where a source spec's text
conflicts with §2–§4, **this document wins and the source spec gets an in-place fix** —
listed in §6.

---

## 1. Three Questions, Three Owners

| Spec | Question it answers | Enforcement it adds | Built |
|---|---|---|---|
| `2026-08-04-security-tailor-design.md` | Which controls apply to **this product**? | dev-time build gate (`check_coverage.py`) | Phase 1 shipped, 4 gaps; Phase 2 (`sast_scan.py`) 0% |
| `2026-08-11-security-kit-mechanism-inventory-design.md` | Are the kit's **claims about itself** true? | **none, by design** (its §11) | 0% |
| `2026-08-04-runtime-tool-mediation-design.md` | Is the **deployed agent's** tool call mediated? | runtime gate (`Security-kit/runtime/`) | 0% — the directory does not exist |

These are not three phases of one project. They are three products with one shared
document set. The tailor gates a *build*; the inventory gates *documents*; the runtime gates
a *deployed tool call*. Only the third is a new enforcement surface.

**Why they must be reconciled rather than merged.** They have different lifetimes. The
tailor and inventory ship with the template; the runtime library ships with a *product built
from* the template. Merging them into one document would force one release cadence onto
three things that do not share one.

**The one concept that genuinely spans all three** is the dev-time → runtime port rule, and
it already has a home: the inventory's `portable_to_runtime` field and its statement that
*the decision travels; the doorway does not*. A pure GATE function ports unchanged; a
DOORWAY (`SEC-HOOK-001`, `can_deny: "n/a"`, `portable_to_runtime: false`) has no runtime
analogue because nobody emits the event. That field is the runtime build's input, and §4
sequences it accordingly.

---

## 2. Seam Resolutions

Seven seams, each with the measurement that found it and one decision.

### Seam 1 — `control-matrix.md` runtime rows (**hard conflict; blocks both builds**)

| Spec | Says |
|---|---|
| runtime §13.2 (`:1194-1198`) | add `SEC-RUNTIME-*` rows, "one row per A1–A5, since those are the claims a reviewer will not otherwise be able to check" |
| inventory §4.2 (`:283-287`) | the runtime's 17 mechanisms "belong in `control-matrix.md` under `SEC-RUNTIME-GAP-001`, **which is where they already are**" |

One row versus five-plus. The conflict is not cosmetic: inventory **I4** (`:424-426`)
requires every `control-matrix.md` row whose status is `MECHANICAL`, `OBSERVE` or `LIBRARY`
to have a `mechanisms.json` row, while inventory §4.2 **excludes** runtime mechanisms from
`mechanisms.json`. So a `SEC-RUNTIME-*` row labelled anything but `GAP` fails I4 the moment
`check_status()` runs. Whoever builds second breaks the other's gate.

**Decision — a `GAP`-scoped naming convention, owned by the inventory spec.**

1. While `Security-kit/runtime/` does not exist, the runtime surface is represented by
   **`SEC-RUNTIME-GAP-001` only** — one row, status `GAP`, as today. I4 exempts `GAP` rows
   by definition, so no `mechanisms.json` entry is required or wanted.
2. Runtime Phase A **may** add per-mechanism rows, but only as `SEC-RUNTIME-GAP-00N` with
   status `GAP`, and only for mechanisms it is about to build. A row flips off `GAP` in the
   **same commit** that adds its `mechanisms.json` row and its passing named proof. Never
   before.
3. `mechanisms.json` describes what is **built**, in any plane. When `policy_core.decide()`
   exists and passes `tests/test_policy_core.py`, it earns a `mechanisms.json` row with
   `category: GATE`, `attaches_at: "Security-kit/runtime/guard.py"`, and
   `portable_to_runtime: true` — it *is* the runtime. The inventory's dev-time-only framing
   in §4.2 is a statement about today's tree, not a permanent boundary.

This preserves both intents: the reviewer gets per-mechanism visibility (runtime's concern)
without any row asserting an unbuilt capability (inventory's concern).

### Seam 2 — runtime §13.4's control count is stale

Runtime §13.4 (`:1208-1211`) says three places call `SECURITY.md` a "40-control reference"
and are off by one. **Measured 2026-08-11 — all three are already correct:**

| Location | Actual text |
|---|---|
| `Security-kit/SECURITY-MANIFEST.md:26` | "41-control reference (source-tagged)" |
| `Security-kit/README.md:24` | "41 source-tagged controls (S1.1 – S8.6)" |
| `findings.md:9` | "41 controls, source-tagged AWS/CSA/OWASP/HARNESS" |

Unique `S<n>.<n>` ids in `SECURITY.md`: **41**. The runtime spec also cites
`README.md:342`; the string is at **line 24**.

**Decision — drop the item from runtime §13.4.** Keep only its real finding: `SECURITY.md`
has `## 1`–`## 9` plus `## References` and **no `§10 Runtime Enforcement`**. That section is
a genuine hole in the reference — none of S1.1–S8.6 states that a deployed agent's tool
calls are mediated at runtime — and it stays in scope for runtime Phase A.

### Seam 3 — runtime §13.5's crosswalk re-tags are already applied

Runtime §13.5 (`:1212-1219`) asks for three honesty fixes. **Measured — all three are in the
working tree already** (uncommitted, `git status` shows `M Security-kit/owasp-crosswalk.md`,
+92/−10):

| Ask | Actual state |
|---|---|
| line 41 ASI01 `[MECH]` → `[OBS]` | `:78` is `[LIB]` + `[GUIDE]`, and names A1 as specified-not-built |
| line 46 ASI06 `[MECH/APP]` → `[GAP]` | `:83` is `[GAP]`, with the `feature_list.json` escalation path spelled out |
| line 47 ASI07 "single-agent" → real gap | `:84` is `[GAP]` and opens "do **not** declare N/A on the grounds that the template is single-agent" |
| line 43 ASI03 "honest — leave it" | `:80` unchanged, still honest |

The line numbers moved because the crosswalk grew; the ASI table now starts at `:74`.

**Decision — replace runtime §13.5 with a pointer to the current crosswalk lines and a note
that the re-tags landed.** An integration checklist that lists completed work as pending is
how a reviewer loses trust in the whole checklist.

### Seam 4 — who owns the `init.sh` test runner

| Spec | Says |
|---|---|
| inventory §10 (`:647`) | add `python3 -m pytest tests/ -q`, non-fatal if pytest absent, closing `SEC-PROOF-GAP-001` |
| runtime §13.1 (`:1190-1193`) | add each new test **by name**, "because `init.sh` has no glob and no pytest runner" |

Both true today: `init.sh` names **6** individual `python3 tests/test_*.py` invocations
(`:79`, `:98`, `:130`, `:142`, `:182`, `:191`) and has **zero** pytest calls. But inventory's
line makes runtime's rationale obsolete.

**Decision — the inventory spec owns the runner; the runtime spec inherits it.**

1. Inventory adds the single `python3 -m pytest tests/ -q` line (its §10, unchanged).
2. Runtime §13.1 changes to: *"`init.sh` runs `pytest tests/ -q` (added by the inventory
   spec). New `tests/test_*.py` files are picked up automatically — no per-file `init.sh`
   edit. Verify with `./init.sh` after adding a test file."*
3. The named invocations stay. They are the stdlib fallback for a tree without pytest, and
   the project constraint is stdlib-only for mechanism code — pytest is a *runner*, not a
   dependency. Every test file keeps its `__main__` block.
4. **Ordering consequence:** if runtime Phase A lands before the inventory, its five new test
   files must be added to `init.sh` by name, and removed again when the pytest line arrives.
   §4 sequences the inventory first to avoid that churn.

### Seam 5 — two writers for `active-controls.md`

`Security-kit/active-controls.md` is generated by `/security-tailor` (tailor §4.5) and
policed by `check_coverage.py:91-99`, which fails if any `applies` control id is absent from
the file's text. Runtime §13.6 (`:1220`) has `/runtime-harden` writing "its runtime section"
into the same file. Two generators, one file, one checker that reads the whole text.

**Decision — one file, two fenced sections, one owner each.**

```markdown
<!-- GENERATED by security-tailor from coverage.json — do not hand-edit -->
# Active security controls
...dev-time applies-controls list — /security-tailor owns everything above the marker...

<!-- BEGIN runtime-harden — generated from Security-kit/runtime/policy.json -->
## Runtime controls (deployed)
...  /runtime-harden owns everything between the markers ...
<!-- END runtime-harden -->
```

Rules: each generator rewrites **only** its own region and preserves the other verbatim.
`check_coverage.py`'s existing `applies`-id assertion scans the whole file, which stays
correct — a substring search does not care which section supplied the id. If
`/runtime-harden` ships before the marker convention, it must not touch this file at all.

### Seam 6 — status vocabularies do not line up

Four vocabularies are in play:

| Source | Tokens |
|---|---|
| `owasp-crosswalk.md` | `[MECH]` `[OBS]` `[LIB]` `[GAP]` `[GUIDE]` `[APP]` |
| inventory `mechanisms.json` | status `MECHANICAL` `OBSERVE` `LIBRARY` `GAP`; category `GATE` `DOORWAY` `RECORD` `SCREEN` `CHECKER` |
| runtime verdicts | `ALLOW` `REQUIRE_APPROVAL` `DENY` |
| runtime tiers | G-tier (M1–M12) / A-tier (A1–A5) |

Inventory I1's synonym map (`:342-352`) covers the first two and deliberately ignores
`[GUIDE]`/`[APP]`. It has **no runtime tokens** — so a runtime status claim in prose would be
*skipped, not checked*, which is precisely the vacuous-check failure mode inventory §11:685
warns about.

**Decision — keep the vocabularies separate; they describe different things.**

- Runtime `ALLOW`/`REQUIRE_APPROVAL`/`DENY` are **verdicts of one call**, not statuses of a
  mechanism. They never enter I1's map. A runtime *mechanism* takes an inventory status like
  any other: `policy_core.decide` is `category: GATE`, `status: MECHANICAL` once built.
- G-tier / A-tier is a **build-order grouping**, not a status. It stays inside the runtime
  spec.
- I1's synonym map is unchanged. What §2 Seam 1 adds is that runtime mechanisms, once built,
  are described in the *existing* vocabulary — so no map extension is needed.

### Seam 7 — the runtime spec's own rev-4 header is unfinished

`2026-08-04-runtime-tool-mediation-design.md` is **uncommitted** (79,650 B, mtime Aug 11
15:16) and internally inconsistent: its rev-4 header promises seven changes (a)–(g); three
landed (the header, the §6.M2 `_bind()` correction, the §6.A2 race + `snapshot()` block).
Still pending: (c) the §14 Phase A1/A2 split, (d) promoting the §13 honesty fixes, (e)
`/runtime-harden` + `validate_policy.py` in §11.6/§11.8, (f) the §11.1 three-zone determinism
table, (g) D2 → Phase A in §15, plus the §16 rev 3→4 changelog entry.

**Decision — de-stale it now, finish it when runtime Phase A is scheduled.** This spec's §6
lists the minimum in-place edits that make it read honestly while parked: revert the header
to rev 3 and record (a)–(g) as an open TODO block, **or** complete (c)–(g). Either is
acceptable; leaving a header that claims changes the body does not contain is not, because
it is the same class of defect the inventory spec exists to catch.

---

## 3. Shared-File Ownership

Six shipped files are written by more than one spec. One owner each; everyone else appends
under a stated rule or defers.

| File | Owner | Rule for the others |
|---|---|---|
| `Security-kit/control-matrix.md` | **inventory** — owns row naming, status labels, I4 | runtime adds only `SEC-RUNTIME-GAP-00N` rows at status `GAP` (Seam 1); tailor adds nothing |
| `Security-kit/mechanisms.json` | **inventory** — sole author | a row appears only when the mechanism is built and its proof passes, in that commit |
| `init.sh` | **inventory** — owns the `pytest tests/ -q` runner line | others add no per-test lines once it exists (Seam 4); the 6 existing named invocations stay as the stdlib fallback |
| `Security-kit/active-controls.md` | **tailor** — owns the file and the pre-marker region | runtime writes only between its `BEGIN/END runtime-harden` markers (Seam 5) |
| `Security-kit/SECURITY.md` | shared by section — §1–§9 are dev-time | runtime adds `§10 Runtime Enforcement` and touches nothing else (Seam 2) |
| `Security-kit/owasp-crosswalk.md` | shared by row | each spec edits only the ASI/LLM rows naming its own mechanisms; status tokens must match `mechanisms.json` or I1 errors |

Two further files are worth naming because they are *unenforced* and easy to forget:

- `Security-kit/SECURITY-MANIFEST.md` — classifies files for `install.sh --no-security`.
  Inventory §10 (`:649-656`) adds `mechanisms.json` as Tier 1 and records the measured
  caveat that **nothing reads the manifest** in `init.sh` or `tests/`, so the row is a
  convention. Runtime's `Security-kit/runtime/` needs no Tier 1 entry — `Security-kit/` is
  deleted wholesale — but its `tests/test_*.py` files do.
- `README.md` / `Security-kit/README.md` — prose. Subject to I1 once `check_status()` exists;
  any status word on a line that also names a `.py` path must agree with `mechanisms.json`.

---

## 4. Build Order

Each step ends with a command that exits 0. No step depends on a later one.

### Step 1 — Finish tailor Phase 1 *(no dependency on the other two specs)*

Its gate is shipped but has never been satisfied: `python3 Security-kit/check_coverage.py`
→ exit **1**, `✗ coverage.json missing — run /security-tailor (fail-closed)`. All 8 plan
tasks landed (`f7809ec`, `583653f`, `000d134`, `a07d847`, `3d64fac` + wiring `9c9f728`,
`cfe53de`, `a8375e4`, `f73fd91`). Four gaps remain:

| Gap | Evidence |
|---|---|
| `coverage.json` never generated | `check_coverage.py` → exit 1 |
| `active-controls.md` still the 7-line stub | file contents, 2026-08-11 |
| no `kiro/steering/active-controls.md` mirror | spec §4.5 requires it; plan Task 4 created only the Claude side — **a spec requirement with no implementing task** |
| §6.5 #7 recall number never produced | `eval_selection.py` → exit 2, "no recorded cases" |

All three of the spec's §8 open questions were resolved by the code in the direction it
proposed: hash scope = sorted non-`.template` `*.md` under `Context/`
(`check_coverage.py:26-33`); location = `Security-kit/coverage.json`; granularity = 20 OWASP
ids (`.claude/commands/security-tailor.md:17`).

**Gate:** `./init.sh` exits 0 **and** `eval_selection.py recorded/` prints a recall number
against the 3-case corpus. The recall figure is an acceptance measurement, not a CI gate —
the scorer is deterministic, the skill that produces the verdicts is not.

### Step 2 — Inventory *(must precede runtime; see Seams 1 and 4)*

Small and self-contained: `mechanisms.json` (10 rows), `check_status()` + synonym map + path
normalisation in `check_coverage.py`, `tests/test_mechanisms.py`, the §6 doc reorganisation,
a `Security-kit/README.md` subsection. Plus its rev-2 in-scope corrections: the
`SEC-EGRESS-001` scope fix, `SEC-PROOF-GAP-001`, the `init.sh` pytest line, the
`SEC-TOOL-001` merge, the manifest row.

It precedes runtime for two mechanical reasons, not for tidiness: it defines the
`SEC-RUNTIME-*` row convention runtime needs (Seam 1), and its `init.sh` runner line removes
runtime's per-test wiring work (Seam 4).

**Gate:** `./init.sh` exits 0 with `check_status()` reporting zero I1–I4 errors and printing
its skip count. A non-zero skip count is expected and acceptable; a *silent* one is not.

### Step 3 — Runtime Phase A *(only when a deployed agent exists to protect)*

Blocked on nothing technical, but it is a different product: it protects the customer's data
and money at runtime, where the dev-time PreToolUse doorway does not exist. Before any code:
apply §6's de-staling edits so §13 stops listing finished work as pending.

Then Phase A per runtime §14 — M1, M2, M3, M4, M5, M8, **A1, A2**. A1 and A2 are Phase A
because they are two of `decide()`'s three arguments; retrofitting `session` later means
rewriting every subscriber.

**Gate:** `pytest tests/ -q` green (picked up automatically after Step 2), plus one
`SEC-RUNTIME-*` row flipped off `GAP` with a `mechanisms.json` row and a passing named
proof, per Seam 1 rule 2.

### Not in any step

- Tailor Phase 2 (`sast_scan.py`, planted-vuln corpus) — gated by tailor §7b:457 on Phase 1's
  recall number being trusted.
- `SEC-PHASE-GAP-001`, the self-promotion defect: `feature_list.json` is not in
  `BUILTIN_PROTECTED_PATHS`, so an Edit is ALLOW and flipping `status: "passing"` takes a
  gated tool from BLOCK to ALLOW. The fix is a `permission.py` patch, and `permission.py` is
  a protected path — **it goes to the user as a patch, not an agent edit.**
- `SEC-COVER-GAP-001` (matcher → `'*'` + internal allowlist), wiring `content_trust.py` into
  an ingestion path, extending `check_egress` beyond shell tokens, back-porting to
  `examples/claims-agent`. Each already recorded, each its own commit.

---

## 5. Vocabulary Map

One table, so a reader of any of the four vocabularies can cross over. Per Seam 6, verdicts
and tiers are deliberately **not** mapped onto statuses.

| Concept | crosswalk | `mechanisms.json` | runtime |
|---|---|---|---|
| Blocks an action, mechanically | `[MECH]` | `status: MECHANICAL`, `category: GATE`, `can_deny: true` | `DENY` returned by `decide()` |
| Records, cannot veto | `[OBS]` | `status: OBSERVE`, `category: RECORD`, `can_deny: false` | M8 audit / M9 monitor |
| Exists, nothing calls it | `[LIB]` | `status: LIBRARY`, `category: SCREEN`, `attaches_at: null` | — |
| Specified, not built | `[GAP]` | no row (`GAP` rows live only in `control-matrix.md`) | any unbuilt M/A mechanism |
| Makes the check run; decides nothing | — | `category: DOORWAY`, `decides: null`, `can_deny: "n/a"` | the dispatcher — **you write it; nobody emits it** |
| Blocks the build, not a call | — | `category: CHECKER` | CI + startup self-check |
| Advice to a human or an app | `[GUIDE]` `[APP]` | **ignored by I1** — not a mechanism status | — |

**The asymmetry worth restating**, because it is the reason two of these specs exist at all:
`[MECH]` in a document is a *claim*; `status: MECHANICAL` in `mechanisms.json` is a claim
with a `proof` command attached. The inventory's whole contribution is making the two agree.

---

## 6. In-Place Fixes to the Source Specs

Minimum edits so no source spec contradicts §2–§4. Each is a documentation change; none
touches mechanism code.

**`2026-08-04-runtime-tool-mediation-design.md`** (currently uncommitted)

| § | Edit | Seam |
|---|---|---|
| header | Resolve rev 4: either complete (c)–(g) or revert to rev 3 with (a)–(g) as an explicit TODO block | 7 |
| §13.1 | Replace per-test `init.sh` naming with "pytest runner added by the inventory spec; new tests are auto-discovered" | 4 |
| §13.2 | Defer row naming to the inventory spec; `SEC-RUNTIME-GAP-00N` at `GAP` only | 1 |
| §13.4 | Delete the 40→41 item (all three sites already say 41); keep `SECURITY.md §10` | 2 |
| §13.5 | Replace the three re-tag asks with a pointer to current crosswalk lines `:78`, `:83`, `:84` and a note that they landed | 3 |
| §13.6 | State the `BEGIN/END runtime-harden` marker rule for `active-controls.md` | 5 |
| §10 | Note that `tests/test_*.py` additions need `SECURITY-MANIFEST.md` Tier 1 rows | §3 |

**`2026-08-11-security-kit-mechanism-inventory-design.md`**

| § | Edit | Seam |
|---|---|---|
| §4.2 | Add: the runtime exclusion is a statement about today's tree; a built runtime mechanism earns a row with `portable_to_runtime: true`. State the `SEC-RUNTIME-GAP-00N` convention normatively | 1 |
| §10 | Add: this spec owns the `init.sh` pytest runner line; other specs inherit it | 4 |

**`2026-08-04-security-tailor-design.md`**

| § | Edit | Seam |
|---|---|---|
| header | Add a rev-4 status block: Phase 1 built (5 commit SHAs), §8's three questions resolved with the `file:line` that resolved each, the 4 remaining gaps, Phase 2 unbuilt | §4 Step 1 |
| §4.5 | State the two-region ownership rule for `active-controls.md` | 5 |
| §7b | Note the missing `kiro/steering/active-controls.md` mirror as a spec requirement with no plan task | §4 Step 1 |

All three also get a one-line cross-reference header naming the other two and this document.

---

## 7. What This Buys, and What It Does Not

**Buys.** A build order in which no step breaks a previous step's gate. One owner per shared
file, so two generators cannot fight over one artifact. Seven contradictions resolved before
either unbuilt spec starts, rather than discovered by a failing `check_status()` afterwards.
Three stale claims in the runtime spec's integration checklist corrected against measurement.

**Does not buy.** No new enforcement — same boundary the inventory spec draws for itself.
Nothing that was a gap stops being a gap. `SEC-PHASE-GAP-001` is still a live
privilege-escalation path. The template remains, in the crosswalk's own words, "a well-built
tool-boundary gate, not agentic-risk coverage."

**Does not buy, specifically.** This document is prose, and **nothing checks it.** Its
ownership table is a convention exactly like `SECURITY-MANIFEST.md` — which the inventory
spec measured as unread by `init.sh` and `tests/`. The only mechanical descendant of this
reconciliation is `check_status()`, and it validates status agreement, not file ownership. If
a future generator writes outside its region in `active-controls.md`, the failure surfaces
as a confusing diff, not a red build.

**One thing worth noticing about the method.** Every conflict in §2 was found by reading the
three specs against the tree and against each other — the stale control count, the already-
applied crosswalk re-tags, the I4-versus-§4.2 contradiction. None required running code,
because none of the code exists yet. That is the same argument the inventory spec makes
about itself, and it is the reason these seams were worth resolving on paper first.
