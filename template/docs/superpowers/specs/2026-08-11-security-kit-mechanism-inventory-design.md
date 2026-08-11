# Security-Kit Mechanism Inventory — One Source of Truth, Checked by Code

**Status:** Draft for review
**Date:** 2026-08-11
**Author:** brainstormed with Yuan Shi
**Scope:** Make the Security-Kit's *own* status claims machine-checked, and document the
procedure that turns a product design document into per-component security
implementation. Adds one data file and one checker function. Builds no new enforcement.

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

Nothing compares them, so they drift silently. Two instances found by reading:

- `Security-kit/README.md:51` describes `content_trust.py` as "data plane — screens
  untrusted content" while `:56` of the same diagram says "LIBRARY — not wired into any
  path yet". Both are in the same code block.
- `Security-kit/SECURITY.md:27` previously described `screen_record()` as enforcement
  ("Call it at every point external content enters"). It is called from `tests/` only.
  Corrected by hand this session — exactly the failure mode a checker prevents.

No test failed for either. **Adequacy review cannot catch this class of defect** because
the reviewer reads one document at a time.

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

| `decides` | `attaches_at` | `can_deny` | `proof` | ⇒ status |
|---|---|---|---|---|
| ✓ | ✓ | true | ✓ | `MECHANICAL` |
| ✓ | ✓ | false | ✓ | `OBSERVE` |
| ✓ | **null** | — | ✓ | `LIBRARY` |
| null | — | — | — | `GAP` (lives in `control-matrix.md`, not here) |

Status becomes checkable rather than merely copied: it is either consistent or
inconsistent with the other cells.

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
    }
  ]
}
```

### 4.1 The rows

Nine, not the "~6" estimated during brainstorming — the count rose because the gates
inside `permission.py` are separate mechanisms with separate proofs, and
`check_coverage.py` is a `CHECKER` row. All cells below were read from source on
2026-08-11.

| id | category | decides | attaches_at | can_deny | status |
|---|---|---|---|---|---|
| `SEC-SELF-001` | GATE | `permission.py::check_protected_paths` | PreToolUse `pre:governance-check` | true | MECHANICAL |
| `SEC-CMD-001` | GATE | `permission.py::check_deny_list` | PreToolUse `pre:governance-check` | true | MECHANICAL |
| `SEC-PHASE-001` | GATE | `permission.py::check_phase_gate` | PreToolUse `pre:governance-check` | true | MECHANICAL |
| `SEC-EGRESS-001` | GATE | `permission.py::check_egress` | PreToolUse `pre:governance-check` | true | MECHANICAL |
| `SEC-POLICY-001` | GATE | `permission.py::_load_json` / `PolicyError` | PreToolUse `pre:governance-check` | true | MECHANICAL |
| `SEC-SECRET-001` | GATE + DOORWAY | `Security-kit/secret_scan.py::main` | PreToolUse `pre:secret-block` | true | MECHANICAL |
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

### 4.2 What is deliberately excluded

- **The runtime spec's 17 mechanisms** (M1–M12 G-tier, A1–A5 A-tier). Including them
  would make 11+ rows read "not built" and turn the inventory into a roadmap. They belong
  in `control-matrix.md` as `GAP` rows, which is where they already are.
- **`GAP` rows generally.** The inventory describes what is *built*. `control-matrix.md`
  describes what is *claimed, including gaps*. Different questions, different files.
- **`demo/`.** `demo/ARCHITECTURE.md:3` states the demo is not the enforcement path.

---

## 5. The Checker: `check_status()` in `check_coverage.py`

A new function alongside `check()`, called from the same `__main__`. Returns
`(error_count, messages)` and contributes to the existing non-zero exit, so `init.sh`
gains a failure mode without gaining a new invocation.

### I1 — Agreement

Every document that states a status for a mechanism states the **same** status as
`mechanisms.json`.

Implementation: for each row id, scan `control-matrix.md`, `owasp-crosswalk.md` and
`Security-kit/README.md` for that id; extract any status token near it via the
vocabulary map below; fail on disagreement.

| Canonical | Accepted synonyms found in the repo |
|---|---|
| `MECHANICAL` | `[MECH]`, `MECHANICAL`, `Mechanical.` |
| `OBSERVE` | `[OBS]`, `OBSERVE`, `Observe` |
| `LIBRARY` | `[LIB]`, `LIBRARY`, `Library only.` |
| `GAP` | `[GAP]`, `GAP`, `Gap.` |

`[GUIDE]` and `[APP]` are **not** statuses of a template mechanism — they describe
advisory guidance and application responsibility. They are ignored by I1, which keys on
the mechanism id, not on tag presence.

### I2 — Coherence

The declared `status` matches what `category` + `attaches_at` + `can_deny` + `proof`
imply, per the table in §3.1. A row claiming `MECHANICAL` with `attaches_at: null` fails.

This is the invariant that catches the `content_trust.py` class of defect: describing a
library as enforcement becomes a build failure rather than a review miss.

### I3 — Proof exists and runs

Every non-null `proof` names a file that exists, and that file is reachable from
`init.sh`. A proof nobody runs is not a proof.

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
- `SEC-EGRESS-001` is a real mechanism and gets `MECHANICAL` plus the inventory row in
  §4.1.
- `SEC-TOOL-001` ("Only approved tools may execute") describes the same code as
  `SEC-PHASE-001` — `check_phase_gate` returning `not in allowlist`. Implementation
  **merges it into `SEC-PHASE-001`** rather than creating a second inventory row for one
  function. Two matrix ids pointing at one mechanism is precisely the duplication this
  spec exists to remove.

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
| Gate mechanics, order, fail-closed behaviour | `governance/ARCHITECTURE.md` | link. `Security-kit/README.md` currently mentions the gates 16 times vs `ARCHITECTURE.md`'s 4 — inverted ownership |
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
  └──────────────┘
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
| `case_i4_catches_matrix_orphan` | a `MECHANICAL` matrix row with no inventory row fails |
| `case_i4_exempts_gap_rows` | the seven `*-GAP-*` rows do not trigger I4 |
| `case_path_spelling_normalised` | `content_trust.py` and `Security-kit/content_trust.py` compare equal |
| `case_i4_rejects_unlabelled_row` | a non-placeholder matrix row with no status label fails (§5.1) |
| `case_malformed_inventory_fails_closed` | unparseable `mechanisms.json` ⇒ error, never pass |

Fail-closed matches `check()`: a missing or malformed `mechanisms.json` is an error, not a
skip.

**Regression baseline to preserve:** 46 tests passing; `control-matrix.md` parsing to 20
rows through the real `parse_matrix`, with `SEC-XXX-001` the only placeholder. `init.sh`
currently reports `FAIL — 5 error(s), 2 warning(s)` because `coverage.json` is absent;
this spec must not change that count except by adding `check_status()` failures if the
inventory is genuinely inconsistent.

---

## 9. Failure Modes of This Design

| Mode | Consequence | Mitigation |
|---|---|---|
| A pipe character inside a new matrix cell | `parse_matrix` does `line.strip().strip("\|").split("\|")` and needs ≥5 cells, mapping col 0 → col 3 — any stray pipe silently corrupts the row | I4 turns silent corruption into a loud orphan error |
| The inventory becomes a roadmap | 11 "not built" rows drown the 9 real ones | §4.2 excludes unbuilt mechanisms by rule |
| A status is *agreed* everywhere and *wrong* everywhere | I1 passes; the claim is still false | I2 checks against structure, not against other prose. Beyond that, adequacy is human |
| Synonym map goes stale as docs are reworded | I1 silently stops matching | `case_shipped_inventory_passes` runs against the real docs, so a rewording that breaks matching fails the suite |
| Line-number citations rot | already happened — `permission.py:99-101`, `:171-180`, `:26-29` are stale after Gate 1a was inserted | `mechanisms.json` cites `file::function`, never line numbers |

---

## 10. Scope Boundary

**In:** `Security-kit/mechanisms.json`; `check_status()` + synonym map + path
normalisation in `check_coverage.py`; `tests/test_mechanisms.py`; the §6 doc
reorganisation; a new `Security-kit/README.md` subsection for the §2 procedure.

**Out — each already recorded, each its own commit:**

- `SEC-PHASE-GAP-001`, the measured self-promotion defect — `feature_list.json` is not in
  `BUILTIN_PROTECTED_PATHS`, so an Edit is ALLOW and flipping `status: "passing"` takes a
  gated tool from BLOCK to ALLOW. Needs a `permission.py` patch, which is a protected
  path: **goes to the user as a patch, not an agent edit.**
- `SEC-COVER-GAP-001`, `matcher` → `'*'` plus an internal allowlist.
- Wiring `content_trust.py` into an ingestion path.
- Extending `check_egress` beyond shell tokens.
- Back-porting to `examples/claims-agent`.
- Stale text in the runtime spec §8/§12 and three `kiro/hooks/` defects.

---

## 11. What This Buys, and What It Does Not

**Buys:** a false status claim in any Security-Kit document becomes a build failure. The
mechanism list stops being reconstructable only by reading five files. The dev-time →
runtime port has a table saying which parts survive. The design-doc → implementation
procedure is written down instead of implied.

**Does not buy:** any new enforcement. Nothing that was a gap stops being a gap. The
template remains, in the crosswalk's own words, "a well-built tool-boundary gate, not
agentic-risk coverage."
