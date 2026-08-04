# Security-Tailor — Design Spec

**Status:** Draft for review
**Date:** 2026-08-04
**Scope:** Approach A (skill + coverage artifact + init.sh gate), "start small"
**Author:** brainstormed with Yuan Shi

---

## 1. Problem & Goal

### The gap
Today the Security-kit connects to a specific AI product only by hand. Its knowledge is
generic and passive:

- `Security-kit/SECURITY.md` — 40 source-tagged controls (AWS / CSA / OWASP / HARNESS).
- `Security-kit/owasp-crosswalk.md` — LLM01–10 + ASI01–10 → template mechanism.
- `Security-kit/control-matrix.md` — ships blank (2 example rows + 1 placeholder); a
  human is expected to fill it.

Nothing actively answers the project-specific question: **"Given THIS product (in
`Context/`), which of these controls apply, which are N/A, and which are gaps?"** The
crosswalk is generic; the matrix starts empty; the bridge between them is manual and
usually skipped.

### The goal
Add a small, active layer that reads the product definition in `Context/`, reasons over
the guidance in `SECURITY.md` + `owasp-crosswalk.md`, and produces a **checkable**
verdict of control applicability — such that an applicable control left without mapped
verification **fails `init.sh`**. Reasoning proposes; a test enforces completeness.

### Non-goals (explicit scope cuts)
- **No new controls.** The skill maps product → *existing* guidance only. It does not
  invent project-specific controls. (Deferred: Approach C.)
- **No policy diffs.** The skill does not propose edits to `deny-list.json` /
  `mcp-allowlist.json`. (Deferred: Approach C.)
- **No verification authoring.** The skill decides *applicability*; the **engineer**
  supplies the verification command in the matrix. The skill only *flags* applicable
  controls that are still unmapped.
- **No adequacy judgment.** The gate proves an applicable control *has* a verification
  mapped — not that the verification is *good*. Adequacy stays human (review-evidence
  column + sign-off).
- **No new hook.** Reasoning is a skill; enforcement is a script called by `init.sh`.
  Nothing runs on every tool call.

---

## 2. Context — what the layer reads and writes

### Inputs (read-only)
| Source | What the skill extracts |
|---|---|
| `Context/*.md` (product-design, architecture, ai-stack, deployment) | attack surface: untrusted inputs, tools the agent calls, egress hosts, data flows, RAG?, multi-agent?, cloud/on-prem |
| `Security-kit/SECURITY.md` | the 40 controls and their intent |
| `Security-kit/owasp-crosswalk.md` | the 20 OWASP ids (LLM01–10, ASI01–10) and the template mechanism for each |

### Outputs (written)
| Artifact | New? | Content |
|---|---|---|
| `Security-kit/coverage.json` | ⭐ new | machine-readable verdict: one entry per OWASP id → `applies` / `n_a` / `gap`, a one-line `reason` grounded in a `Context/` citation, and (for `applies`) the `matrix_row` id it expects |
| `Security-kit/control-matrix.md` | exists | for each `applies` id, a row with objective + impl location filled, **verification column left blank** for the engineer |
| chat gap report | — | the `n_a` + `gap` lists with reasons, so the engineer records residual-risk decisions |

### The binding triangle
```
  coverage.json  ──"applies" ids──►  control-matrix.md  ──rows──►  check_coverage.py
   (skill writes)                     (engineer fills verify)       (init.sh gate)
        ▲                                                                │
        └────────────── regenerated whenever Context/ changes ◄──────────┘
```
This converts a *reasoning* output (which controls apply — inherently advisory) into a
*checkable* state (are all applicable controls mapped to evidence — mechanically gated).

---

## 3. Triggers — when it runs

Three entry points, all invoking the **same** skill (idempotent — safe to re-run):

| # | Trigger | Where it wires | Why here |
|---|---|---|---|
| T1 | **At init** | `/init-project` gains Step 2b: invoke security-tailor right after `Context/` is read | product definition is fresh in context — cheapest moment to select controls |
| T2 | **On demand** | `/security-tailor` command, run by hand anytime | re-tailor after any change; also the recovery path if T1 was skipped |
| T3 | **At phase sign-off** | `/session-cycle` sign-off step: re-run, ask "did this phase add a tool / egress / data flow / untrusted input?" | the crosswalk itself says "re-verify after any change that adds a tool, egress, retrieval, or data flow" — phase transitions are exactly those moments |

T2 is the same entry point as T1/T3, just human-invoked. There is no separate "standalone"
code path — the skill only depends on `Context/` + `SECURITY.md`, so it always runs
standalone by construction.

---

## 4. Implementation — the four pieces (start small)

### 4.1 `security-tailor` skill
- **Files:** `.claude/commands/security-tailor.md` (Claude) + `kiro/steering/security-tailor.md` (Kiro mirror).
- **Behavior (documented steps, like `/init-project`):**
  1. Read every non-template file in `Context/`. If `Context/` has only its README +
     `.template` stubs → **stop**, ask the engineer to add a product doc first (mirrors
     `/init-project` precondition).
  2. For each of the 20 OWASP ids in `owasp-crosswalk.md`, decide `applies` / `n_a` /
     `gap`, each with a **one-line reason that cites a `Context/` line**. No citation →
     the id is reported as "cannot determine" (a flagged gap), never guessed.
  3. Write `coverage.json`. Add/update `applies` rows in `control-matrix.md` (verification
     left blank). Print the `n_a` + `gap` report to chat.
  4. Remind the engineer to fill verification cells, then run `./init.sh`.
- **Guardrails:** the skill treats `Context/` as trusted project docs but does NOT execute
  anything from them; it only reads and classifies.

### 4.2 `Security-kit/coverage.json` (schema)
```jsonc
{
  "schema_version": 1,
  "generated_from": "Context/ @ <sha256-of-concatenated-context-files>",
  "generated_note": "produced by security-tailor; do not hand-edit — re-run the skill",
  "controls": [
    { "id": "LLM01", "verdict": "applies", "reason": "reads untrusted claim text (Context/product-design.md:12)", "matrix_row": "SEC-INPUT-001" },
    { "id": "LLM08", "verdict": "n_a",     "reason": "no retrieval/vector store in architecture (Context/architecture.md)" },
    { "id": "ASI03", "verdict": "gap",     "reason": "cloud deploy, no identity broker (Context/deployment.md:8)" }
  ]
}
```
- `verdict ∈ {applies, n_a, gap}`. Only `applies` requires a `matrix_row`.
- `generated_from` carries a content hash of `Context/` for staleness detection.

### 4.3 `Security-kit/check_coverage.py` (stdlib, ~60–80 lines)
Pure-function checker, no deps. **Fails closed.** Exit non-zero on any of:

1. `coverage.json` **missing** → fail (this is what forces the skill to have run).
2. `coverage.json` **stale**: recomputed `Context/` hash ≠ `generated_from` hash → fail
   ("Context changed; re-run /security-tailor").
3. For every `applies` id: a matching `control-matrix.md` row exists **and** its
   verification cell is non-empty (and not `TODO`/`TBD`/`{{...}}`).
4. `coverage.json` is malformed / not the expected shape → fail.

Emits a human-readable list of exactly which ids/rows are the problem (mirrors how
`init.sh` reports unfilled placeholders). It does **not** judge verification quality.

### 4.4 `tests/test_coverage.py` (ground-truth, like `test_fixtures.py`)
Proves the checker:
- **fails** when an `applies` control has no matrix row (T-neg-1),
- **fails** when the row exists but verification is blank/TODO (T-neg-2),
- **fails** when coverage.json is stale vs Context/ hash (T-neg-3),
- **fails** when coverage.json is missing (T-neg-4, fail-closed),
- **passes** when every `applies` control has a non-empty verification (T-pos-1),
- **passes** (skips cleanly) when there are zero `applies` controls (T-pos-2).

---

## 5. Binding into the main template (add/omit + observability)

Rides the **existing** A/B machinery — no new toggle. Registers into the Tier 1 / Tier 3
split from `SECURITY-MANIFEST.md`, consumed by `install.sh --no-security`.

### 5.1 Wiring edits (existing files)
1. **`init.sh`** — inside block 5b (`if [ -d "governance" ]`, line ~112), add:
   `python3 Security-kit/check_coverage.py` → on non-zero, `ERRORS++`. Placed with the
   other integrity checks (engine present, gate wired, hook proof).
2. **`.claude/commands/init-project.md`** — add Step 2b (invoke security-tailor).
3. **`.claude/commands/session-cycle.md`** + `kiro/steering/session-cycle.md` — add the
   sign-off re-tailor step.
4. **`Security-kit/README.md`** + `Security-kit/control-matrix.md` — document the new flow
   and the "skill fills objective/location, you fill verification" division.

### 5.2 add/omit registration
- **`Security-kit/SECURITY-MANIFEST.md`**
  - Tier 1 (deleted by `--no-security`): `security-tailor.md`, `check_coverage.py`,
    `test_coverage.py`, `coverage.json`, `kiro/steering/security-tailor.md`.
  - Tier 3 (neutralized in place): the `check_coverage.py` line in `init.sh`; the
    `/init-project` Step 2b; the `/session-cycle` sign-off step.
- **`install.sh`**
  - add the new files to `TIER1=(...)` (line ~62).
  - add one `sed` to strip the `check_coverage.py` line from `init.sh` (mirror of the
    existing governance-JSON strip at line ~89).

### 5.3 What you observe (the A/B contrast)
| Scenario | Full build | `--no-security` build |
|---|---|---|
| Product adds a data flow, control never mapped | `check_coverage.py` fails → `init.sh` **cannot go green** | no coverage gate → `init.sh` **passes silently** |
| `coverage.json` | present, fresh, gates | absent |
| Security reasoning | ran at init + every sign-off | never ran |

This adds a **sharper failure mode** to the template's existing A/B story (full build
24/24 vs no-security 16/24 in `SECURITY-MANIFEST.md`): "you extended the attack surface
without extending control coverage" now shows as a red board.

### 5.4 "Missed it in init" is not silent
If `/init-project` skips Step 2b → `coverage.json` never generated → `check_coverage.py`
fails on rule 1 (missing) → `init.sh` **FAIL**, naming the missing artifact. Fix = run
`/security-tailor` once (T2). The `--no-security` build is the only place the check is
stripped, so a deliberately ungoverned project isn't nagged for a file it removed —
covered for free by the `if [ -d "governance" ]` guard.

---

## 6. Evaluation — how we know it works

### 6.1 Unit / integration (mechanical, CI-able)
- `tests/test_coverage.py` (§4.4) — the checker's ground truth. Wired into `init.sh`
  block 4 alongside the other tests.
- `init.sh` on a fresh full copy: **FAILs** citing missing `coverage.json` (proves the
  gate has teeth). After `/security-tailor` + filled verifications: **PASS**.

### 6.2 End-to-end on the reference example
Use the existing `examples/claims-agent/` as the E2E subject:
- Run `/security-tailor` against its `Context/`. Expect: LLM01 (untrusted claim) →
  `applies`; LLM08 (vector) → `n_a`; a plausible `gap`. Verdicts must cite claims-agent
  Context lines.
- Confirm `init.sh` goes red with a blank verification, green once mapped.

### 6.3 A/B differential (the template's own evaluation idiom)
- Full build vs `install.sh --no-security` on the same product-with-a-new-dataflow:
  full fails the coverage gate; no-security passes. Record in the existing
  `TEMPLATE-EVALUATION-REPORT.md` style.

### 6.4 Quality checks on the reasoning (human, sampled)
Because reasoning is inherently advisory, sample the verdicts:
- **Grounding:** does every verdict cite a real `Context/` line? (no citation = fail)
- **False-N/A audit:** for a product WITH retrieval, does it correctly flip LLM08 to
  `applies`? (guards the dangerous direction — under-claiming coverage)
- **Idempotence:** re-running with unchanged `Context/` produces an identical
  `coverage.json` (stable hash, stable verdicts).

### 6.5 Success criteria
1. Fresh full build cannot reach `init.sh` PASS without a coverage pass.
2. `/security-tailor` runs standalone from just `Context/`.
3. `--no-security` cleanly strips all four new pieces; that build still passes its own
   (reduced) `init.sh`.
4. Every verdict in `coverage.json` carries a `Context/` citation.
5. Zero new runtime dependencies (stdlib python + bash only).

---

## 7. Advice / recommendation

1. **Ship §4 + §5 only. Defer C.** The applicability gate is the whole value of "start
   small." Policy-diff generation and invented controls are a clean *second* phase once
   the coverage loop is trusted.
2. **Fail-closed on missing coverage.json is the load-bearing decision.** If the checker
   "skips when absent," the entire gate becomes advisory and the enhancement collapses
   into today's status quo. Treat absent = fail (except in `--no-security`).
3. **Keep the skill's scope to classification.** The strongest failure mode for an
   LLM-driven security step is *over-reach* — inventing controls, editing policy,
   hand-waving verifications. The narrow "applies/n_a/gap + cite" contract is what keeps
   it trustworthy and testable.
4. **Guard the under-claiming direction explicitly.** A wrong `n_a` (saying a control
   doesn't apply when it does) silently drops coverage — worse than a wrong `applies`
   (which just adds a harmless matrix row). The false-N/A audit (§6.4) is the priority
   eval.
5. **State the adequacy boundary in the docs.** The gate enforces *completeness* of
   coverage, not *quality* of each control. Overclaiming this is the one way the feature
   could mislead. Say it plainly in `Security-kit/README.md`.
6. **Reuse, don't parallel-build.** Every new piece mirrors an existing template idiom
   (policy JSON ↔ `mcp-allowlist.json`; checker ↔ `permission.py`; ground-truth test ↔
   `test_fixtures.py`; init.sh gate ↔ block 5b). This keeps it native, not bolted on.

---

## 8. Open questions for the engineer
1. **Context hash scope** — hash all of `Context/`, or only the docs the skill actually
   read? (Proposal: all non-template `.md` in `Context/`, sorted, concatenated.)
2. **coverage.json location** — `Security-kit/coverage.json` (proposed) vs alongside the
   matrix. Either works; Security-kit/ keeps security artifacts together.
3. **Granularity** — verdict per OWASP id (20 rows, proposed) vs per SECURITY.md control
   (40 rows). OWASP ids are coarser and map 1:1 to the crosswalk the engineer already
   reviews — recommended for "start small."
