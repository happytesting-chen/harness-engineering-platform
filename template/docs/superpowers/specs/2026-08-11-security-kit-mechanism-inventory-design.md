# Security-Kit Mechanism Inventory — One Source of Truth, Checked by Code

**Status:** Draft for review (rev 2 — supersedes rev 1)
**Date:** 2026-08-11 (rev 2: 2026-08-11)
**Author:** brainstormed with Yuan Shi
**Scope:** Make the Security-Kit's *own* status claims machine-checked, and document the
procedure that turns a product design document into per-component security
implementation. Adds one data file and one checker function. Builds no new enforcement.

**Read alongside** — three specs, three different questions; none subsumes another:
| Spec | Question |
|---|---|
| [`2026-08-04-security-tailor-design.md`](2026-08-04-security-tailor-design.md) | Which controls apply to THIS product? (dev-time build gate) |
| **this spec** | Are the kit's claims about itself true? (adds no enforcement — §11) |
| [`2026-08-04-runtime-tool-mediation-design.md`](2026-08-04-runtime-tool-mediation-design.md) | Is the DEPLOYED agent's tool call mediated? (0% built) |
| [`2026-08-11-security-kit-build-reconciliation-design.md`](2026-08-11-security-kit-build-reconciliation-design.md) | **Read this first** — resolves the seams between the three and fixes the build order |

This spec owns two things the other two defer to it for: the **`init.sh` test runner** (§10.1)
and the **`SEC-RUNTIME-GAP-00N` naming convention** (§4.2).

> **Rev 2 changes.** Rev 1's design stands — the asymmetry in §1 is real and the fix is
> right. Rev 2 fixes what re-measuring found: **I1 as written is a no-op**, **I3 as written
> fails on the shipped tree**, and four stated numbers are wrong.
>
> | # | Change | Why |
> |---|---|---|
> | (a) | **I1 rewritten.** Its join key — the `SEC-` id — appears in only one document. Measured: outside `control-matrix.md`, the *whole repo* contains 4 `SEC-` id mentions, and 3 of those are `SEC-COVER-GAP-001`. I1 would scan two files, match nothing, and pass forever (§5.I1) | a green check that verifies nothing is worse than no check — it converts an unknown into a false assurance |
> | (b) | **I3 relaxed to "reachable from a named runner", and the reachability gap recorded as a finding.** `tests/test_protected_paths.py` (19 tests) and `tests/test_steady_state.py` (5 tests) are **not invoked by `init.sh`** — yet `test_protected_paths.py` is the cited proof for `SEC-SELF-001` and `SEC-POLICY-001`, the two rows that protect the mechanism itself (§5.I3) | I3 as written would fail on the shipped tree. That is I3 working — so the finding is recorded, not the invariant weakened away |
> | (c) | **Row count 9 → 10.** `SEC-HOOK-001` is a `MECHANICAL` matrix row and was missing from §4.1, which I4 would have caught as an orphan — rev 1's own invariant, failing against rev 1's own table (§4.1) | the omission is evidence for the spec's thesis; fixing it silently would waste that |
> | (d) | **Four measured numbers corrected** (§4.1, §6, §8) — GAP rows 7 → **8**; `README.md` gate mentions 16 → **23** (and `ARCHITECTURE.md` 4 → **6**); matrix rows parse to **20** ✓ confirmed; 46 tests ✓ confirmed | rev 1 stated four figures; two were wrong, and §9's last row is about exactly this rot |
> | (e) | **`SEC-EGRESS-001` demoted from `MECHANICAL` to `OBSERVE`-at-best**, or its objective narrowed | its own matrix row's Verification cell reads "Egress fixture or E2E test" — prose, not a command — and `SEC-EGRESS-GAP-001` says egress is checked for `bash` only. Rev 1 gave it `MECHANICAL` + a `true` `can_deny`, which I2 should reject (§5.1) |
> | (f) | **`mechanisms.json` added to `SECURITY-MANIFEST.md`**, and the manifest's unenforced status noted | measured: nothing in `init.sh` or `tests/` reads `SECURITY-MANIFEST.md`, so the tier list is itself an unchecked claim — the same defect class, one file over (§10) |

> **What this is not.** This spec does not close any of the measured gaps
> (`SEC-COVER-GAP-001`, `SEC-PROMPT-GAP-001`, `SEC-RESULT-GAP-001`,
> `SEC-SEQUENCE-GAP-001`, `SEC-PHASE-GAP-001`, `SEC-INTERP-GAP-001`,
> `SEC-RUNTIME-GAP-001`). It makes them impossible to *misdescribe*. Fixing them is
> separate work with separate commits and tests.

---

## 1. The Problem

The kit answers two questions. One is machine-checked; the other is prose.

| | **Q1** | **Q2** |
|---|---|---|
| The question | "Does **this product** have risk X?" | "Does **the template** actually stop X?" |
| Subject | the product being built — different in every copy | the template's own code — identical in every copy |
| Evidence that answers it | `Context/*.md` — product design, AI stack, deployment target, architecture, scope (the document types listed in `Context/README.md`) | files on disk: `governance/permission.py`, `.claude/settings.json`, `tests/` |
| Why the author differs | that evidence is **prose written fresh per project**. Nobody has read it yet, so reading-and-classifying *is* the job — which is what `/security-tailor` does | that evidence is **fixed code shipped with the template**. The maintainer already read it; there is nothing to discover |
| Where the answer lands | `Security-kit/coverage.json` → `Security-kit/active-controls.md` | **nowhere structured today** |
| What checks the answer | `check_coverage.py` — `check()` Rule 3: every `applies` control maps to a `control-matrix.md` row with a non-placeholder Verification | **nothing** |

A model appears in Q1 only because Q1's input is unread prose. That is a property of the
input, not a position about models. Given a filled-in threat model, Q1 would be
hand-authored too.

### 1.1 The measured symptom

Q2's answer is currently stated as adjectives in four documents using four different
vocabularies. Read 2026-08-10:

| Document | Vocabulary |
|---|---|
| `Security-kit/owasp-crosswalk.md:7-14` | `[MECH]` `[LIB]` `[GUIDE]` `[APP]` `[GAP]` (+ `[OBS]` used in rows) |
| `Security-kit/control-matrix.md:8-13` | `MECHANICAL` `OBSERVE` `LIBRARY` `GAP` |
| `Security-kit/README.md:238-248` | English sentences — "Mechanical.", "Library only.", "Gap.", "Does not exist." |
| `docs/superpowers/specs/2026-08-04-runtime-tool-mediation-design.md` | `[MECH]` `[OBS]` `[APP]` |

Nothing compares them, so they drift silently.

> **Rev 2 withdraws rev 1's first example.** Rev 1 claimed `README.md:51` contradicts `:56`.
> Re-read: lines 46–56 are a **two-column ASCII diagram**, and those two lines sit in
> *different columns* — `:51`'s left column is `permission.py`, `:56`'s right column is
> `content_trust.py`, which it correctly labels `LIBRARY — not wired into any path yet`. The
> diagram is consistent. Rev 1 misread column-adjacent text as sequential prose.
>
> Recording the withdrawal rather than deleting it, because it is evidence for the same
> thesis from the other direction: **a human reading carefully still got a cross-document
> status claim wrong** — in a spec whose entire purpose is cross-document status agreement.
> It also sets a design constraint: I1 must be **line-scoped** (§5.I1). A document-scoped
> matcher would reproduce this exact false positive, mechanically and forever.

The one confirmed instance:

- `Security-kit/SECURITY.md:27` previously described `screen_record()` as enforcement
  ("Call it at every point external content enters"). It is called from `tests/` only.
  Corrected by hand this session — exactly the failure mode a checker prevents. The
  corrected text now reads "**Data plane — LIBRARY, NOT ENFORCEMENT**" and "**But nothing in
  this template calls it**" (`SECURITY.md:26-30`, read 2026-08-11), consistent with
  `SEC-CONTENT-001`.

And the one rev 2 found, which is stronger than either: **`SEC-EGRESS-001` claims "network
actions stay within approved destinations" and no code implements destination control** (§5.1).

No test failed for any of these. **Adequacy review cannot catch this class of defect** because
the reviewer reads one document at a time — and, as the withdrawn example shows, may misread
even the one document in front of them.

### 1.2 The asymmetry, stated once

Q1's answer is a declared file that code checks. Q2's answer is scattered prose that
nothing checks. **The fix is to give Q2 the treatment Q1 already has.**

---

## 2. Design Document → Security Implementation, Per Component

This is the procedure the kit performs but has never written down. Five steps; **only
step 1 requires judgement.**

```
  1. READ the design doc     →  which components exist, what each one touches
  2. LIST the boundaries     →  every place data or authority crosses
  3. PICK a category         →  the boundary TYPE determines it (§3)
  4. DERIVE the attach point →  the category says WHERE inside that component
  5. DERIVE the proof        →  the attach point says which test is possible
```

`/security-tailor` performs step 1 and produces `coverage.json`. Steps 2–5 are
deterministic given step 1's output plus the category table in §3.

### 2.1 Worked example

Design doc states: *"the agent reads a claim record from Postgres, decides approve/deny,
emails the customer, and appends the decision to a ledger."* Risk IDs are the
`owasp-crosswalk.md` rows.

| Component (named in the design doc) | Boundary crossed | Risk | Category | Attach point *inside that component* | What proves it |
|---|---|---|---|---|---|
| DB read of the claim body | untrusted text → model context | LLM01, ASI01, ASI06 | **SCREEN** | inside the read function, before the text returns to the loop — no interception event exists here, so it must be a call | injected record → control field dropped, instruction-shaped text flagged |
| the approve/deny decision | reasoning | LLM06 | **none exists** | — | — never claim one; the model is not a control surface |
| email send | irreversible external effect | LLM02, ASI02, ASI05 | **DOORWAY + GATE** | the dispatcher between "proposal" and "call" | unapproved recipient → DENY **and no email sent** |
| SMTP/API host reached | network | LLM02 (S3.1) | **GATE** (egress) | same dispatcher, host check on the URL argument | unlisted host → DENY |
| ledger append | accountability + integrity | ASI09, ASI10 | **RECORD + GATE** | record after the verdict; ledger path in the protected list | every verdict appears; agent write to the ledger → DENY |
| refund total *across* the session | sequence, not a call | ASI08, LLM10 | **GATE with state** | dispatcher, cumulative counter | **GAP** — runtime spec §4 A2, unbuilt |

Illustrative: assembled from the crosswalk rows and `Context/README.md`'s document types,
not read from a filled-in `Context/` directory.

Two properties this makes visible that prose did not:

- **The category is forced by the boundary, not chosen.** Content entering the model has
  no interception event — `PostToolUse` cannot block, so screening must be a call. That
  is *why* `content_trust.py` is a library rather than a hook. An outbound action does
  have an interception event. The implementer does not get to pick.
- **The last row is how a gap gets found rather than argued.** "Refund total" is not a
  single call, so no per-call gate can express it. The trace produces the gap.

---

## 3. What a Mechanism Row Is — the Category Axis

A mechanism is not one object. It is up to four parts, and the categories are simply
*which parts are present*.

| Plain name | What it is | Fails by | Portable to runtime? |
|---|---|---|---|
| **DOORWAY** | the thing that makes the check run before the action | not being attached | ✗ rewrite |
| **GATE** | pure decision: input → ALLOW / DENY | deciding wrong | ✓ as-is |
| **RECORD** | writes what happened; cannot stop it | never being read | ✓ |
| **SCREEN** | inspects content, returns a report, caller decides | nobody calling it | ✓ |
| **CHECKER** | build-time program that blocks the *build*, not a tool call | not being run | n/a → CI |

**The decision travels; the doorway does not.** `check_deny_list`, `check_egress`,
`check_phase_gate` and `check_protected_paths` are pure functions and port to a deployed
agent unchanged. The pre-tool event is a property of Claude Code and vanishes in
production. This is why `decides` and `attaches_at` are separate columns: the same table
tells you what carries to runtime and what must be rebuilt (`SEC-RUNTIME-GAP-001`).

### 3.1 Status is derived from the cells, not asserted

| `category` | `decides` | `attaches_at` | `can_deny` | `proof` | ⇒ status |
|---|---|---|---|---|---|
| GATE | ✓ | ✓ | true | ✓ | `MECHANICAL` |
| RECORD | ✓ | ✓ | false | ✓ | `OBSERVE` |
| SCREEN | ✓ | **null** | false | ✓ | `LIBRARY` |
| **DOORWAY** | **null** | ✓ | **n/a** | ✓ | `MECHANICAL` |
| CHECKER | ✓ | ✓ (a runner) | n/a | ✓ | `MECHANICAL` |
| — | null | null | — | — | `GAP` (lives in `control-matrix.md`, not here) |

Status becomes checkable rather than merely copied: it is either consistent or
inconsistent with the other cells.

**`category` is part of the key, not decoration** (rev 2). Rev 1 derived status from four
cells and read `decides: null` as `GAP` — which mis-classifies `SEC-HOOK-001`, a wired
doorway that decides nothing and is fully mechanical (§4.1). The distinction rev 1 lost:

```
  decides ✓ + attaches_at null  →  a decision nothing invokes   → LIBRARY
  decides null + attaches_at ✓  →  an invocation point          → MECHANICAL (as a DOORWAY)
  both null                     →  nothing                      → GAP
```

`can_deny` is `n/a`, not `false`, for DOORWAY and CHECKER — neither returns a verdict, so
`false` would wrongly push them to `OBSERVE`. The schema must distinguish `null`/`n/a` from
`false`; a JSON `false` and a missing key cannot mean the same thing here.

---

## 4. The Artefact: `Security-kit/mechanisms.json`

Hand-authored. One row per **existing** mechanism. Not generated, not model-written.

```json
{
  "schema": 1,
  "mechanisms": [
    {
      "id": "SEC-SELF-001",
      "category": "GATE",
      "decides": "governance/permission.py::check_protected_paths",
      "attaches_at": ".claude/settings.json PreToolUse pre:governance-check",
      "can_deny": true,
      "proof": "python3 -m pytest tests/test_protected_paths.py -q",
      "status": "MECHANICAL",
      "portable_to_runtime": true
    },
    {
      "id": "SEC-HOOK-001",
      "category": "DOORWAY",
      "decides": null,
      "attaches_at": ".claude/settings.json PreToolUse",
      "can_deny": "n/a",
      "proof": "python3 -m pytest tests/test_hooks.py -q",
      "status": "MECHANICAL",
      "portable_to_runtime": false
    }
  ]
}
```

**Field notes (rev 2).** Two cells carry meaning that a naive reading loses:

- **`can_deny` is tri-valued** — `true`, `false`, or the string `"n/a"`. A DOORWAY and a
  CHECKER return no verdict, so `false` would push them to `OBSERVE` via §3.1. `null` is not
  used, because a missing key and "this question does not apply" must stay distinguishable.
- **`decides: null` + `attaches_at` set is legal and means DOORWAY**, not `GAP` (§3.1). Both
  null means `GAP`, and `GAP` rows do not live in this file at all (§4.2).
- **`portable_to_runtime` is `false` for every DOORWAY** by definition — the pre-tool event is
  a property of Claude Code (§3). It is not a judgement call per row; §3's table fixes it from
  `category`, so `check_status()` could derive it. It stays an explicit column because the
  runtime spec's port table reads it directly, and a derived value that is only ever read is a
  worse trade than a stated one that I2 can contradict.

### 4.1 The rows

**Ten** (rev 1 said nine), up from the "~6" estimated during brainstorming — the gates
inside `permission.py` are separate mechanisms with separate proofs, `check_coverage.py` is a
`CHECKER` row, and rev 1 **omitted `SEC-HOOK-001`**. All cells below were read from source on
2026-08-11.

| id | category | decides | attaches_at | can_deny | status |
|---|---|---|---|---|---|
| `SEC-SELF-001` | GATE | `permission.py::check_protected_paths` | PreToolUse `pre:governance-check` | true | MECHANICAL |
| `SEC-CMD-001` | GATE | `permission.py::check_deny_list` | PreToolUse `pre:governance-check` | true | MECHANICAL |
| `SEC-PHASE-001` | GATE | `permission.py::check_phase_gate` | PreToolUse `pre:governance-check` | true | MECHANICAL |
| `SEC-POLICY-001` | GATE | `permission.py::_load_json` / `PolicyError` | PreToolUse `pre:governance-check` | true | MECHANICAL |
| `SEC-SECRET-001` | GATE + DOORWAY | `Security-kit/secret_scan.py::main` | PreToolUse `pre:secret-block` | true | MECHANICAL |
| **`SEC-HOOK-001`** | **DOORWAY** | **null — it decides nothing** | `.claude/settings.json` PreToolUse | n/a | MECHANICAL |
| `SEC-EGRESS-001` | GATE | `permission.py::check_egress` | PreToolUse `pre:governance-check` | true | **see §5.1 — not MECHANICAL as-is** |
| `SEC-AUDIT-001` | RECORD | `Harness-Best-Practice/observability/audit.py::record` | PostToolUse `post:audit-capture` | **false** | OBSERVE |
| `SEC-CONTENT-001` | SCREEN | `Security-kit/content_trust.py::screen_record` | **null** | false | LIBRARY |
| `SEC-COVERAGE-001` | CHECKER | `Security-kit/check_coverage.py::check` | `init.sh` — `python3 Security-kit/check_coverage.py` | n/a | MECHANICAL |

Cells verified 2026-08-11: gate functions are defined in `governance/permission.py`
(`check_deny_list`, `check_protected_paths`, `check_phase_gate`, `check_egress`,
`_load_json` raising `PolicyError`); hook ids `pre:governance-check`, `pre:secret-block`
and `post:audit-capture` are as spelled in `.claude/settings.json`; `screen_record` and
`record` are the public entry points of `content_trust.py` and
`observability/audit.py`. `SEC-POLICY-001` is listed as a GATE because fail-closed
denial is a decision the gate returns, not a separate attach point — it shares
`pre:governance-check` with the other four.

> #### `SEC-HOOK-001` — rev 1's omission is the spec's own thesis, in miniature
>
> It is a `MECHANICAL` row in `control-matrix.md:32` and it was missing from rev 1's table.
> **I4 would have flagged it as a matrix orphan** — so rev 1's inventory failed rev 1's own
> invariant, found not by review but by running the join by hand.
>
> It also forces a schema decision rev 1's §3.1 could not express: `SEC-HOOK-001` is a
> **pure DOORWAY**. It decides nothing; it asserts *"the gate is actually wired."* So
> `decides: null` must NOT imply `GAP` — §3.1's fourth row is wrong as stated, and §3.1 gains
> the DOORWAY case. This row is why `category` and `status` cannot be collapsed into one
> column: a doorway with no decision is fully mechanical, and a decision with no doorway is a
> `LIBRARY`.
>
> Its `proof` is `tests/test_hooks.py`, which asserts the wiring rather than any verdict —
> and which `init.sh` does invoke, so it satisfies I3 today.

### 4.2 What is deliberately excluded

- **The runtime spec's 17 mechanisms** (M1–M12 G-tier, A1–A5 A-tier — counted from its §6
  headings, 2026-08-11). **All 17 are unbuilt**: `Security-kit/runtime/` does not exist.
  Including them would make every one of those rows read "not built" and turn a
  what-is-shipped inventory into a roadmap. They belong in `control-matrix.md` under
  `SEC-RUNTIME-GAP-001`, which is where they already are.
- **`GAP` rows generally.** The inventory describes what is *built*. `control-matrix.md`
  describes what is *claimed, including gaps*. Different questions, different files.
- **`demo/`.** `demo/ARCHITECTURE.md:3` states the demo is not the enforcement path.

#### The exclusion is about today's tree, not about runtime forever

Stated as a rule so the runtime spec can rely on it (see
[`2026-08-11-security-kit-build-reconciliation-design.md`](2026-08-11-security-kit-build-reconciliation-design.md)
§2 Seam 1). The first bullet excludes those 17 mechanisms **because they are unbuilt**, not
because they are runtime. Once one is built and proven it is an ordinary row like any other —
`Security-kit/runtime/policy_core.py` is a path the same way `governance/permission.py` is.

What makes this load-bearing rather than a nicety: **I4** requires every non-`GAP` row in
`control-matrix.md` to have a `mechanisms.json` row, and this section excludes unbuilt runtime
mechanisms from that file. A `SEC-RUNTIME-*` row at `MECHANICAL`, `OBSERVE` or `LIBRARY` would
therefore fail `check_status()` the moment it is added. So, normatively:

1. **Naming.** Unbuilt runtime surface uses `SEC-RUNTIME-GAP-00N`, status **`GAP`**. Today
   `N = 1` covers the whole surface (`control-matrix.md:51`). The runtime spec's Phase A may add
   `SEC-RUNTIME-GAP-002`, `-003`, … at status `GAP` for mechanisms it is about to build. `GAP`
   rows are exempt from I4's second clause ("*a gap has no mechanism*", **I4** below), so any
   number of them is safe. Note the exemption is only from *that* clause: I4's first clause
   still binds, so a `GAP` row must not appear in `mechanisms.json` at all — which is the same
   rule read from the other side.
2. **Flipping off `GAP`.** A row leaves `GAP` in the **same commit** that adds its
   `mechanisms.json` row and its passing named proof. Never in a commit of its own — a row that
   claims `MECHANICAL` one commit before its proof exists is precisely the defect §1 measured,
   and it would break `init.sh` for everyone in between.
3. **Renaming.** When a row flips, drop the `-GAP-` infix: `SEC-RUNTIME-GAP-002` →
   `SEC-RUNTIME-002`. The id encodes the claim, so the id changes when the claim does. Both
   documents are edited in that one commit, so I1 never sees a mismatch.
4. **The row that arrives is an ordinary row**, with one cell already answered: a built runtime
   mechanism gets **`portable_to_runtime: true`** by construction — it *is* the runtime. The
   flag stays meaningful because it keeps distinguishing GATE from DOORWAY *within* the runtime:
   `policy_core.decide()` is portable to the next host, `guard.py`'s wrapper and the dispatcher
   are not (runtime spec §14's A1/A2 split rests on exactly this line). A `true` on every runtime
   row would make the column vacuous — and a vacuous cell is what §1 is about.

This inventory spec owns that convention because it owns the checker that enforces it. The
runtime spec **defers** to this section rather than restating it (its §13.2).

---

## 5. The Checker: `check_status()` in `check_coverage.py`

A new function alongside `check()`, called from the same `__main__`. Returns
`(error_count, messages)` and contributes to the existing non-zero exit, so `init.sh`
gains a failure mode without gaining a new invocation.

### I1 — Agreement

Every document that states a status for a mechanism states the **same** status as
`mechanisms.json`.

> #### ⚠ Rev 1's I1 was a no-op. Measured.
>
> Rev 1 said "for each row id, scan `control-matrix.md`, `owasp-crosswalk.md` and
> `README.md` for that id." **The id is not in those documents.** Counted 2026-08-11:
>
> | Document | `SEC-` ids present |
> |---|---|
> | `Security-kit/control-matrix.md` | 20 — it is the id registry |
> | `Security-kit/owasp-crosswalk.md` | 2, both `SEC-COVER-GAP-001` |
> | `Security-kit/README.md` | 1, `SEC-COVER-GAP-001` |
> | `Security-kit/SECURITY.md` | 1, `SEC-CONTENT-001` |
>
> So I1 would join on a key that exists in one file, match nothing in the other three, find
> zero disagreements, and **report success for the rest of the project's life** — while the
> `README.md:51` vs `:56` contradiction that motivated this spec sat untouched, because
> neither of those lines contains a `SEC-` id.
>
> This is the worse failure mode. A missing check leaves a known unknown; a check that
> passes vacuously manufactures confidence. §9 gains a row for it.

**Rev 2 — I1 keys on the implementation path, not the id.** A path is what the prose
actually contains. Measured co-occurrence of a status token and a `.py` path on the same
line: `README.md` 4 lines, `owasp-crosswalk.md` 13 lines — real joins, not zero.

```
  for each mechanism row:
      key = normalised(decides.split("::")[0])        # e.g. Security-kit/content_trust.py
      for each doc in (control-matrix, owasp-crosswalk, README, SECURITY):
          for each LINE mentioning key:
              tokens = status_tokens(line)            # vocabulary map below
              if tokens and canonical(tokens) != row.status:  → ERROR
```

**Line-scoped, not document-scoped.** A document mentioning a path and, 200 lines later,
using the word "Mechanical" about something else is not a disagreement. The claim and its
subject must sit on one line — which is how these tables are written anyway.

| Canonical | Accepted synonyms found in the repo |
|---|---|
| `MECHANICAL` | `[MECH]`, `MECHANICAL`, `Mechanical.` |
| `OBSERVE` | `[OBS]`, `OBSERVE`, `Observe` |
| `LIBRARY` | `[LIB]`, `LIBRARY`, `Library only.` |
| `GAP` | `[GAP]`, `GAP`, `Gap.` |

`[GUIDE]` and `[APP]` are **not** statuses of a template mechanism — they describe advisory
guidance and application responsibility, and a single row legitimately carries both a status
and a `[GUIDE]` note (`owasp-crosswalk.md:78` is `[LIB]` + `[GUIDE]`). I1 ignores them
rather than treating the pair as a conflict.

**Known limit, stated rather than hidden.** `permission.py` appears on 35 lines across the
four documents and hosts five separate mechanisms, so a path key cannot say *which* gate a
line means. For those five rows I1 additionally requires the **function name** on the line
(`check_egress`, `check_deny_list`, …); a line naming only `permission.py` is unattributable
and skipped. Measured, 6 lines in `owasp-crosswalk.md` and 2 in `README.md` carry a status
token with no path at all — also skipped. **I1 therefore checks agreement among
attributable claims; it does not claim to see every sentence.** The skip count is printed,
so shrinking coverage is visible rather than silent.

### I2 — Coherence

The declared `status` matches what `category` + `attaches_at` + `can_deny` + `proof`
imply, per the table in §3.1. A row claiming `MECHANICAL` with `attaches_at: null` fails.

This is the invariant that catches the `content_trust.py` class of defect: describing a
library as enforcement becomes a build failure rather than a review miss.

### I3 — Proof exists and runs

Every non-null `proof` names a file that exists, and that file is reachable from a named
runner. A proof nobody runs is not a proof.

> #### ⚠ I3 fails on the shipped tree today — and it is right to
>
> Measured 2026-08-11, per-file, with `init.sh` reachability:
>
> | Test file | Tests | Invoked by `init.sh`? |
> |---|---|---|
> | `tests/test_hooks.py` | 10 | ✓ |
> | `tests/test_content_trust.py` | 6 | ✓ |
> | `tests/test_e2e.py` | 3 | ✓ |
> | `tests/test_fixtures.py` | 1 | ✓ |
> | `tests/test_coverage.py` | 1 | ✓ |
> | `tests/test_eval_selection.py` | 1 | ✓ |
> | **`tests/test_protected_paths.py`** | **19** | **✗ NO** |
> | **`tests/test_steady_state.py`** | **5** | **✗ NO** |
>
> `test_protected_paths.py` is the cited Verification for **`SEC-SELF-001` and
> `SEC-POLICY-001`** (`control-matrix.md:27-28`) — the two rows asserting that the agent
> cannot rewrite its own mechanism and that a bad policy denies. It is also the file pinning
> `SEC-INTERP-GAP-001` so that gap "cannot close silently." **24 of the tree's 46 tests, and
> the entire self-protection proof, run only if a human types the command.**
>
> `init.sh` invokes no `pytest` at all (measured: zero occurrences), while five matrix rows
> cite `python3 -m pytest …` as their Verification. The commands are correct and pass — `46
> passed` via `python3 -m pytest tests/ -q` — they are simply not what `./init.sh` runs.
>
> **This is I3 doing its job on its first run.** Do not weaken I3 to make it green.

**Resolution — two steps, in this order:**

1. **Record the finding.** New matrix row `SEC-PROOF-GAP-001`: *"the self-protection proof
   is not in the default runner"* — measured, with the table above. It is a real gap in the
   same sense as the other eight.
2. **Then satisfy I3 mechanically.** `init.sh` gains one line —
   `python3 -m pytest tests/ -q` — which makes every test file reachable, closes
   `SEC-PROOF-GAP-001`, and lets I3 pass by *fixing the tree* rather than by lowering the
   bar. Confirmed to pass as-is: `46 passed in 0.50s`.

**Reachability is defined as: named in `init.sh`, or matched by a directory-wide runner
`init.sh` invokes.** After step 2 the second clause covers all eight files, so I3 does not
have to enumerate them and will not silently exempt a ninth file added later.

`pytest` is a **runner**, not a dependency of the mechanism code: every test file also has a
stdlib `__main__` block and passes under bare `python3`. The zero-external-deps rule binds
mechanism code; step 2 must keep the `pytest` line non-fatal when `pytest` is absent, exactly
as `init.sh` already degrades when `python3` is missing.

### I4 — No orphans, both directions

- Every `mechanisms.json` id appears in `control-matrix.md`.
- Every `control-matrix.md` row whose status is `MECHANICAL`, `OBSERVE` or `LIBRARY` has
  a `mechanisms.json` row. `GAP` rows are exempt by definition — a gap has no mechanism.

### 5.1 Unlabelled matrix rows

Three `control-matrix.md` rows carry **no** status label (measured 2026-08-11):
`SEC-TOOL-001`, `SEC-EGRESS-001`, and the `SEC-XXX-001` template row. I4 keys on the
label, so these need a decision before it can run:

- `SEC-XXX-001` is the per-project placeholder — **exempt**, matched by the existing
  `PLACEHOLDER_RE`.
- `SEC-TOOL-001` ("Only approved tools may execute") describes the same code as
  `SEC-PHASE-001` — `check_phase_gate` returning `not in allowlist`. Implementation
  **merges it into `SEC-PHASE-001`** rather than creating a second inventory row for one
  function. Two matrix ids pointing at one mechanism is precisely the duplication this
  spec exists to remove.
- `SEC-EGRESS-001` — **rev 1 said "is a real mechanism and gets `MECHANICAL`". That is the
  exact error this spec exists to prevent.** Three measurements say otherwise:

  | Evidence | Reading |
  |---|---|
  | its Verification cell is `Egress fixture or E2E test` (`control-matrix.md:26`) | **prose, not a command.** No `proof` value can be honestly written, so I3 has nothing to check |
  | `check_egress` matches five substrings — `curl `, `wget `, `nc `, `ssh `, `nmap ` (`permission.py:257`) | a token blocklist, not destination control. `ncat`, a tab separator, or `python3 -c "import urllib…"` all pass |
  | it is reached only when `tool == "bash"`; `WebFetch` never routes to any gate (`SEC-COVER-GAP-001`, `SEC-EGRESS-GAP-001`) | the primary egress channel bypasses it entirely |

  Its objective as written — *"Network actions stay within approved destinations"* — is
  **false**, and rev 1 was about to make a checker certify it. Two honest options; pick one
  in implementation:

  1. **Narrow the objective to what the code does** — *"blocks five known network shell
     tokens in `bash` commands"* — status `MECHANICAL`, `proof` a real fixture asserting
     those five tokens deny. Defensible and small.
  2. **Label it `OBSERVE`**, keeping the broad objective, with `SEC-EGRESS-GAP-001` carrying
     the remainder.

  **Option 1 is recommended**: `check_egress` genuinely denies, so `OBSERVE` understates it;
  what was wrong was the *scope* of the claim, not its mechanism. Either way
  `SEC-EGRESS-GAP-001` stays, because neither option makes `WebFetch` gated.

  This row is the strongest evidence for the whole spec: a `MECHANICAL` label on a
  destination-control claim that no code implements survived every prior review, and was
  about to be promoted into a machine-checked file where it would have read as verified.

I4 must therefore treat an unlabelled, non-placeholder row as an **error**, not a skip —
otherwise the cheapest way to pass the checker is to delete a status.

### 5.2 Path normalisation

Path spellings vary across documents (`content_trust.py` vs
`Security-kit/content_trust.py`, measured). `check_status()` compares
project-root-relative `PurePosixPath` forms, never raw strings.

### 5.3 What `check_status()` does not do

It does not judge whether a mechanism is *good*, whether a proof is *sufficient*, or
whether the category was chosen *wisely*. Consistent with the existing coverage gate, it
enforces **completeness and agreement**, never **adequacy**. Adequacy stays with human
review and sign-off.

---

## 6. Document Ownership — One Fact, One Owner

Reorganisation, not rewriting. Each fact gets exactly one authoritative home; every other
mention becomes a reference.

| Fact | Owner | Everyone else |
|---|---|---|
| Status of each shipped mechanism | `Security-kit/mechanisms.json` | reference the id; do not restate the adjective |
| Gate mechanics, order, fail-closed behaviour | `governance/ARCHITECTURE.md` | link. `Security-kit/README.md` says "gate" **23** times vs `ARCHITECTURE.md`'s **6** (measured 2026-08-11; rev 1 said 16 vs 4) — inverted ownership |
| Control text (S1.1–S8.6) | `Security-kit/SECURITY.md` | cite the S-number |
| Risk → mechanism, incl. gaps | `Security-kit/owasp-crosswalk.md` | cite the OWASP id |
| Control → code → test → evidence, per project | `Security-kit/control-matrix.md` | cite the `SEC-` id |
| The five loop positions and the four ✗s | `Security-kit/README.md` §2 | link |
| Design-doc → implementation procedure (§2) | `Security-kit/README.md` (new subsection) | link |
| Which controls apply to this product | `Security-kit/coverage.json` | link |
| Runtime (deployed) design | `docs/superpowers/specs/2026-08-04-runtime-tool-mediation-design.md` | link |

Status adjectives stay where they read naturally — the earlier decision was "status may
appear anywhere; the checker verifies all copies agree." I1 is what makes that safe.

---

## 7. Dev-Time vs Runtime — the Two "Hows"

At development phase there are exactly **two** ways a mechanism is enforced. Not two
styles — two different targets.

```
  HOW #1 — THE DOORWAY YOU RENT              protects: the repo, and the mechanism
  ─────────────────────────────              itself, from the agent that is building

  agent proposes a tool call
        │
        │   the host emits a pre-tool event   ← you did NOT write this loop.
        ▼                                       You rent a chokepoint.
  ┌──────────────┐   permission.py reads JSON on stdin
  │  GATE (×5)   │   exit 2 → BLOCKED.  anything else → PROCEEDS
  │  + secret    │   ①a protected-paths · ① deny-list · ② phase · ③ egress
  │    scanner   │   · policy-load fail-closed;  then pre:secret-block
  └──────────────┘   (two separate hooks, same matcher string)
        │
        ▼  tool runs → RECORD (append-only; cannot veto)

  Coverage is a STRING: the matcher names five tools
  (Bash|Write|Edit|MultiEdit|NotebookEdit). Anything unnamed reaches
  no gate at all — the gate is correct and NOT THERE (SEC-COVER-GAP-001).


  HOW #2 — THE CHECKER YOU RUN               protects: the documents from drifting
  ────────────────────────────               off the code

  ./init.sh
        │
        ├─ tests/             is each GATE correct?
        │                     measured: 6 of 8 files invoked — 22 of 46 tests.
        │                     test_protected_paths.py (19) and test_steady_state.py
        │                     (5) run only by hand.        (§5.I3 adds the missing line)
        ├─ check_coverage.py  is every "applies" control mapped to a
        │                      verification?               (completeness)
        └─ check_status()     do all status claims agree, and do they match
                               the structural cells?        (NEW — I1–I4)
        │
        ▼  exit ≠ 0 → the SESSION is blocked, not a tool call
```

**#1 cannot stop a false claim in a document. #2 cannot stop an action.** Neither
substitutes for the other; that is why both exist. This spec adds only to #2.

| | **Dev-time — live today** | **Runtime — specified, not built** |
|---|---|---|
| Who provides the chokepoint | the host emits pre-tool events | **nobody.** You write the dispatcher |
| Denial expressed as | process exit 2 | raise / return DENY before the call |
| Coverage determined by | a matcher string in `.claude/settings.json` | whether **every call site** routes through the dispatcher |
| Typical silent bypass | a tool you forgot to name | one direct SDK call that skips the dispatcher |
| What is protected | the repo, the mechanism, the builder | the customer, the data, the money |
| GATE reusable? | — | **✓ pure functions, port as-is** |
| DOORWAY reusable? | — | **✗ must be rewritten** |
| CHECKER | `init.sh` before commit | no analogue; becomes CI + a startup self-check |

---

## 8. Testing

New file `tests/test_mechanisms.py`, following the existing style of
`tests/test_coverage.py` — stdlib only, `case_*` functions, `sys.path` insert of
`Security-kit/`.

| Case | Asserts |
|---|---|
| `case_shipped_inventory_passes` | the real `mechanisms.json` + real docs yield 0 errors |
| `case_i1_catches_disagreement` | a fixture doc claiming `MECHANICAL` for a `LIBRARY` row fails |
| `case_i2_catches_unwired_mechanical` | `status: MECHANICAL` with `attaches_at: null` fails |
| `case_i2_accepts_observe` | `can_deny: false` + wired + proof ⇒ `OBSERVE` passes |
| `case_i3_catches_missing_proof_file` | a `proof` naming a nonexistent file fails |
| `case_i4_catches_matrix_orphan` | a `MECHANICAL` matrix row with no inventory row fails — the `SEC-HOOK-001` case, §4.1 |
| `case_i4_exempts_gap_rows` | the **eight** `*-GAP-*` rows do not trigger I4 (rev 1 said seven) |
| `case_path_spelling_normalised` | `content_trust.py` and `Security-kit/content_trust.py` compare equal |
| `case_i4_rejects_unlabelled_row` | a non-placeholder matrix row with no status label fails (§5.1) |
| `case_malformed_inventory_fails_closed` | unparseable `mechanisms.json` ⇒ error, never pass |
| `case_i1_matches_on_path_not_id` | a fixture doc with a wrong status **and no `SEC-` id** is still caught — pins the rev-1 no-op (§5.I1) |
| `case_i1_skips_unattributable_line` | a status token on a line naming only `permission.py` is skipped, and counted in the printed skip total |
| `case_i1_ignores_guide_and_app` | a `[LIB]` + `[GUIDE]` line passes — both tags on one row is legal |
| `case_i2_doorway_is_mechanical` | `decides: null` + `attaches_at` set ⇒ `MECHANICAL`, not `GAP` (§3.1) |
| `case_i2_rejects_can_deny_false_for_doorway` | `can_deny: false` on a DOORWAY fails; `n/a` passes — `false` must not silently mean `OBSERVE` |
| `case_i3_requires_named_runner` | a `proof` file existing but reachable from no runner fails (§5.I3) |

Fail-closed matches `check()`: a missing or malformed `mechanisms.json` is an error, not a
skip.

### 8.1 Regression baseline — measured 2026-08-11, not recalled

| Fact | Value | How measured |
|---|---|---|
| Total tests | **46 passed** | `python3 -m pytest tests/ -q` |
| Test files | **8** | `tests/test_*.py` |
| Files `init.sh` invokes | **6 of 8** | `test_protected_paths.py` and `test_steady_state.py` excluded — §5.I3 |
| `parse_matrix` rows | **20** | called on the real `control-matrix.md` |
| Placeholder rows | **1** (`SEC-XXX-001`) | `PLACEHOLDER_RE` over parsed cells |
| GAP rows | **8** | unique `SEC-*-GAP-001` ids (rev 1 said 7) |
| `init.sh` result | `FAIL — 5 error(s), 2 warning(s)` | `./init.sh`, `coverage.json` absent |

This spec must not change the error/warning counts except by adding `check_status()`
failures where the inventory is genuinely inconsistent. Note the interaction with §5.I3: the
`pytest tests/ -q` line raises the test count reachable from `init.sh` from 22 to 46 — a
**coverage** change, not a pass/fail change, since all 46 already pass.

`test_coverage.py` and `test_eval_selection.py` collect as **1 pytest test each** because
they use internal `case_*` functions under one `test_all` — 10 and 4 cases respectively.
`tests/test_mechanisms.py` follows that same style, so it will add **1** to the pytest count
while carrying the 11 cases above.

---

## 9. Failure Modes of This Design

| Mode | Consequence | Mitigation |
|---|---|---|
| A pipe character inside a new matrix cell | `parse_matrix` does `line.strip().strip("\|").split("\|")` and needs ≥5 cells, mapping col 0 → col 3 — any stray pipe silently corrupts the row | I4 turns silent corruption into a loud orphan error |
| The inventory becomes a roadmap | 17 "not built" rows drown the 10 real ones | §4.2 excludes unbuilt mechanisms by rule |
| A status is *agreed* everywhere and *wrong* everywhere | I1 passes; the claim is still false | I2 checks against structure, not against other prose. Beyond that, adequacy is human. **`SEC-EGRESS-001` is a live example** (§5.1) — every document agreed, and the objective was still false |
| Synonym map goes stale as docs are reworded | I1 silently stops matching | `case_shipped_inventory_passes` runs against the real docs, so a rewording that breaks matching fails the suite |
| **A check that passes vacuously** | worse than no check: it converts a known unknown into a false assurance. **This already happened** — rev 1's I1 joined on the `SEC-` id, which 3 of its 4 target documents do not contain, so it would have reported success forever (§5.I1) | every invariant states its **join key** and prints its **skip count**. A rising skip count means shrinking coverage, visibly. `case_i1_matches_on_path_not_id` pins it |
| The scope of a claim is wrong while the mechanism is real | I2 passes — the cells are coherent — and the objective sentence still overstates. `check_egress` denies five shell tokens; its row claims "approved destinations" | no invariant reads objective prose. **Structural coherence is not scope correctness**, and pretending otherwise is how rev 1 nearly certified `SEC-EGRESS-001`. Scope stays with human sign-off |
| The manifest listing security files is itself unchecked | measured: nothing in `init.sh` or `tests/` reads `SECURITY-MANIFEST.md`, so its tier assignments are unverified claims — the same defect class this spec fixes, one file over | out of scope here; recorded in §10 so it is a known gap rather than an assumption |
| Line-number citations rot | already happened — `permission.py:99-101`, `:171-180`, `:26-29` are stale after Gate 1a was inserted | `mechanisms.json` cites `file::function`, never line numbers |

---

## 10. Scope Boundary

**In:** `Security-kit/mechanisms.json` (10 rows, §4.1); `check_status()` + synonym map + path
normalisation in `check_coverage.py`; `tests/test_mechanisms.py`; the §6 doc
reorganisation; a new `Security-kit/README.md` subsection for the §2 procedure.

**Added by rev 2, in scope because each is a false-or-vacuous claim rather than new
enforcement:**

| Item | Change | Section |
|---|---|---|
| `SEC-EGRESS-001` scope correction | narrow the objective to the five shell tokens, or relabel `OBSERVE`; write a real `proof` command in place of the prose cell | §5.1 |
| `SEC-PROOF-GAP-001` | new matrix row: the self-protection proof is not in the default runner | §5.I3 |
| `init.sh` gains `python3 -m pytest tests/ -q` | non-fatal if `pytest` absent; makes all 8 test files reachable and closes the row above | §5.I3 |
| **This spec owns that one line** | every later spec inherits it instead of adding per-test invocations — see below | §5.I3 |
| `SEC-TOOL-001` merge | fold into `SEC-PHASE-001`; one mechanism, one row | §5.1 |
| `SECURITY-MANIFEST.md` | add `Security-kit/mechanisms.json` as Tier 1 | below |

The manifest edit is in scope for a reason worth stating: this spec adds a security file, and
the manifest is what tells `install.sh --no-security` to remove it. Omitting the row would
ship a kit whose `--no-security` install leaves an orphaned `mechanisms.json` behind and whose
`check_status()` then fails on a tree that deliberately has no security kit. **Measured
caveat:** nothing reads `SECURITY-MANIFEST.md` in `init.sh` or `tests/` — `install.sh` hardcodes
its own `TIER1` bash array (`install.sh:62-69`) and deletes whole directories including
`Security-kit`, so `mechanisms.json` is in fact removed with or without the row. The row is a
convention, not a mechanism — recorded in §9 rather than fixed here.

### 10.1 This spec owns the test runner

The one `python3 -m pytest tests/ -q` line above is **this spec's to add, and no other
spec's**. Stated explicitly because two other specs would otherwise each solve the same problem
differently and collide in the same file (see
[`2026-08-11-security-kit-build-reconciliation-design.md`](2026-08-11-security-kit-build-reconciliation-design.md)
§2 Seam 4):

- **Today:** `init.sh` names **6** test invocations individually (`:79`, `:98`, `:130`, `:142`,
  `:182`, `:191`) and calls `pytest` **zero** times. Two of the 8 test files
  — `tests/test_protected_paths.py`, `tests/test_steady_state.py` — are therefore on disk and
  never run by the default runner. That is `SEC-PROOF-GAP-001`.
- **After this spec:** one glob line runs all 8, and every test file added by any later spec is
  discovered with no `init.sh` edit at all.
- **Therefore:** the runtime spec's §13.1 adds **nothing** to `init.sh`. Its five new
  `tests/test_*.py` files are reachable the moment they exist. Any spec that instead adds its
  own named invocations is re-creating the gap this line closes.

Keep the 6 named invocations. They are not redundant: each prints a specific ✓/✗ line and
contributes a distinct `ERRORS` increment, and the pytest line is deliberately **non-fatal**
when `pytest` is absent — so on a machine with no `pytest`, those 6 remain the enforcement
floor. The glob adds coverage; it does not replace the named gates.

**Out — each already recorded, each its own commit:**

- `SEC-PHASE-GAP-001`, the measured self-promotion defect — `feature_list.json` is not in
  `BUILTIN_PROTECTED_PATHS`, so an Edit is ALLOW and flipping `status: "passing"` takes a
  gated tool from BLOCK to ALLOW. Needs a `permission.py` patch, which is a protected
  path: **goes to the user as a patch, not an agent edit.**
- `SEC-COVER-GAP-001`, `matcher` → `'*'` plus an internal allowlist.
- Wiring `content_trust.py` into an ingestion path.
- Extending `check_egress` beyond shell tokens.
- Back-porting to `examples/claims-agent`.
- ~~Stale text in the runtime spec §8/§12~~ — **fixed in that spec's rev 4**: `_load_json`'s
  fail-open was itself repaired in `70a12a1` and re-verified by driving the real hook, so §8's
  warning box and §12's line citations were corrected there. Three `kiro/hooks/` defects remain
  out of scope.

---

## 11. What This Buys, and What It Does Not

**Buys:** an *attributable* false status claim in any Security-Kit document becomes a build
failure. The mechanism list stops being reconstructable only by reading five files. The
dev-time → runtime port has a table saying which parts survive. The design-doc →
implementation procedure is written down instead of implied.

**Does not buy:** any new enforcement. Nothing that was a gap stops being a gap. The
template remains, in the crosswalk's own words, "a well-built tool-boundary gate, not
agentic-risk coverage."

**Does not buy, specifically** — the limits rev 2 measured rather than assumed:

- **Unattributable claims are skipped, not checked.** 8 lines carry a status token with no
  path (§5.I1). The skip count is printed; it is not zero.
- **Scope errors survive all four invariants.** `SEC-EGRESS-001` was structurally coherent
  and substantively false. I2 checks cells against cells, never a claim against the code's
  actual reach. Only human sign-off catches that.
- **The manifest that classifies security files is itself unchecked** (§9, §10).

**What rev 2 itself demonstrates.** Writing this spec's invariants down and then running them
by hand against the tree found: one vacuous invariant, one invariant that fails on the shipped
code for a real reason, one missing inventory row, one overclaimed control, one withdrawn
example, and four wrong numbers — **before a line of `check_status()` existed.** The value is
in stating the join key and the derivation rule precisely enough to be wrong. That is the
argument for the artefact, made by the process of specifying it.
