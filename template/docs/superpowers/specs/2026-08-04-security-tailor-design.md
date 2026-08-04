# Security-Tailor — Design Spec

**Status:** Draft for review (rev 3 — added tailored static scan + benchmarked effectiveness)
**Date:** 2026-08-04
**Scope:** Two components — (1) tailor (skill → coverage artifact → init.sh gate → dev-time
steering); (2) tailored static scan (`sast_scan.py`) that checks the product's code for the
sinks of the *selected* controls. Both proven by labeled benchmarks (confusion matrix).
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
An **active security layer** so that when Claude Code develops the AI solution, it
follows *this product's* tailored controls — not a generic 40-control list, and not
nothing. "Active" has three layers; this spec delivers all three:

| Layer | "Active" means | Delivered by |
|---|---|---|
| **B — Selection** | "For THIS product, these N of 40 controls apply; these are gaps" | the skill (§4.1) → `coverage.json` (§4.2) |
| **C — Coverage gate** | Can't reach `init.sh` PASS with an applicable control unmapped | `check_coverage.py` (§4.3) |
| **D — Dev-time steering** | While Claude *writes* a risky line (egress, input handling), it is attending to the *applicable* controls for this product | the skill also emits a **tailored steering file** (§4.5) loaded into the agent's working context every session |

Reasoning proposes (B); a test enforces completeness (C); a steering file keeps the
tailored guidance in the agent's attention while it codes (D). Layer D is what makes the
layer "active" during development, not just at checkpoints.

> Relationship to existing enforcement: `permission.py` already *blocks* bad actions
> mechanically (per tool call). Layer D is the *advisory* complement — it shapes what the
> agent does *before* it reaches the gate, focused on the controls that actually apply
> here. Block = mechanical backstop; steering = tailored intent. Both, not either.

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
- **No new hook.** Reasoning is a skill; enforcement is a script called by `init.sh`;
  dev-time steering is a static file loaded via `CLAUDE.md` import. Nothing new runs on
  every tool call — `permission.py` remains the only per-action gate.
- **Layer D does not replace mechanical enforcement.** `active-controls.md` *steers*
  (advisory); it does not *block*. `permission.py` stays the backstop. See §7.7.

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
| `Security-kit/active-controls.md` (+ `kiro/steering/` mirror) | ⭐ new | **layer D** — the tailored steering file: only the *applicable* controls for this product, phrased as dev-time reminders. Generated, not hand-edited. Loaded via a `@import` in `CLAUDE.md` (Claude) and `inclusion: auto` frontmatter (Kiro) — see §4.5 for why NOT `.claude/rules/`. |
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

## 4. Implementation — the pieces (start small)

Two components: **the tailor** (§4.1–4.5 — selects controls, gates coverage, steers dev)
and **the tailored static scan** (§4.6 — checks the product code for the sinks of the
*selected* controls, so "we selected LLM01" is backed by "we actually looked for LLM01
sinks in the code").


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
     left blank). **Generate `Security-kit/active-controls.md` (§4.5)** — the layer-D
     steering file listing only the `applies` controls. Print the `n_a` + `gap` report to chat.
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

### 4.5 `Security-kit/active-controls.md` — the layer-D steering file
The piece that makes the layer active *during development*. Generated by the skill
(step 3); lists **only the `applies` controls** for this product, rewritten as terse
dev-time reminders (not the full 40-row reference).

- **Content shape:**
  ```markdown
  <!-- GENERATED by security-tailor from coverage.json — do not hand-edit; re-run /security-tailor -->
  # Active security controls for {{PROJECT_NAME}}
  These apply to THIS product (derived from Context/). Follow them while developing.

  - **[LLM01] Untrusted input** — claim text is DATA, never commands. Screen with
    `content_trust.screen_record()` before use. (why: reads untrusted claim text)
  - **[LLM02] Egress / secrets** — only `notify_api` host is allowed; never log the
    claimant PII to stdout. (why: cloud deploy sends notifications)
  - **[LLM06] Excessive agency** — one phase at a time; do not call phase-02 tools early.
  ...only the applicable ids, each with its one-line "why" from coverage.json...
  ```
- **Load mechanism (must be a PROVEN auto-load path, not an inert dir):**
  - **Claude:** add one line to `CLAUDE.md` — `@Security-kit/active-controls.md` — next to
    the existing `@Harness-Best-Practice/AGENTS.md` import. This is the SAME import
    mechanism CLAUDE.md already relies on, so it loads every session.
  - **Kiro:** the `kiro/steering/` mirror carries `inclusion: auto` frontmatter (same as
    the existing `kiro/steering/security.md:1-2`), so Kiro auto-includes it.
  - **Explicitly NOT `.claude/rules/`:** that directory does not exist in this template and
    CLAUDE.md does not load it — writing there would be inert (the "unwired = does nothing"
    trap the template warns about). Verified 2026-08-04.
- **Relationship to the generic `SECURITY.md`:** `SECURITY.md` stays as the full reference
  the agent *can* consult; `active-controls.md` is the tailored subset always in context.
  Generic guide = library; active-controls = the shortlist that applies here.
- **Freshness:** regenerated from `coverage.json` on every skill run, so it never drifts
  from the selection. `check_coverage.py` MAY additionally assert it exists and its control
  set matches `coverage.json`'s `applies` set (cheap, keeps D honest) — see §6.1.

### 4.6 `Security-kit/sast_scan.py` — the tailored static scan (SAST-the-capability)
Answers the second effectiveness question: not "did we *select* the right controls" (that
is §4.1) but "does the product's own code *contain* the sinks for the controls we
selected?" It reads `coverage.json`, and for each `applies` control runs the matching
static checks over the product's code.

- **Inputs:** `coverage.json` (which controls to scan for) + the product's own source —
  `tools/*.py`, prompt templates, and `tools/mcp-allowlist.json` (tool scopes).
- **Technique (zero-dep, honest about its limits):** stdlib `ast` walk + regex, the same
  idiom `init.sh:188` already uses (`ast.parse`). It is **heuristic pattern/AST matching,
  not taint-complete** — no interprocedural dataflow like Semgrep/CodeQL. That limit is not
  hidden; it is *quantified* by the benchmark in §6.2. Zero-dep is a template constraint
  (§7.5), and the benchmark is what keeps the heuristic honest.
- **Checks (one family per OWASP id it was told applies):**
  | Selected control | Static check over product code |
  |---|---|
  | LLM01 (prompt injection) | untrusted input reaching a prompt/f-string without `content_trust.screen_record()` |
  | LLM02 (secrets/output) | hardcoded secret patterns in source (reuses `secret_scan.py` regexes) |
  | LLM03 / ASI02-04 (supply chain / tool scope) | wildcard or over-broad entries in `tools/mcp-allowlist.json`; egress host not in allowlist |
  | LLM06 (excessive agency) | `eval(`/`exec(`/`subprocess … shell=True` in tool code |
  | SSRF-class | URL built from untrusted input without host validation |
- **Only scans selected controls.** A `n_a` control is not scanned — the scan *inherits*
  the tailor's selection, so the two components are bound: over-broad selection = wasted
  scan; a missed selection (false `n_a`) means its sinks are never scanned — which is
  exactly why §6's headline metric is the tailor's **recall** (a miss cascades).
- **Output:** findings list (control id, file:line, sink kind) → written to
  `Security-kit/scan-findings.json`. Wired into `init.sh` block 5b as a **warning by
  default** (findings ≠ hard fail, because heuristic FPs shouldn't brick the board); an
  opt-in strict mode escalates to `ERRORS++`. Adequacy of a finding stays human, like the
  matrix review column.
- **Not a replacement for the runtime gate.** `permission.py` blocks at call time;
  `sast_scan.py` inspects code before it runs. Defense in depth, not either/or.

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
4. **`CLAUDE.md`** — add `@Security-kit/active-controls.md` next to the existing
   `@Harness-Best-Practice/AGENTS.md` import (layer-D auto-load). This is the proven
   Claude mechanism; do not use `.claude/rules/` (§4.5).
5. **`Security-kit/README.md`** + `Security-kit/control-matrix.md` — document the new flow
   and the "skill fills objective/location, you fill verification" division.

### 5.2 add/omit registration (audited against real `install.sh`, 2026-08-04)
`install.sh:62-66` deletes Tier 1 as **whole directories** (`governance`, `Security-kit`,
`tests`, plus two `kiro/steering/*` files and `kiro/hooks`) — not file-by-file. Three
consequences for the new pieces, verified by reading `install.sh`:

- **Files under `Security-kit/` and `tests/` need NO new TIER1 entry.** `coverage.json`,
  `check_coverage.py`, `sast_scan.py`, `scan-findings.json`, `active-controls.md`,
  `tests/test_coverage.py` all sit inside dirs `install.sh:63` already `rm -rf`s. Listing
  them individually (as rev 2 did) is redundant and contradicts the dir-level design.
- **The `init.sh` block-5b additions need NO strip.** `check_coverage.py` / `sast_scan.py`
  live inside block 5b, guarded by `if [ -d "governance" ]` (`init.sh:112`). When `--no-security`
  deletes `governance/`, the whole block self-skips — same as every existing 5b check. So
  rev 2's "add a sed to strip check_coverage from init.sh" is **unnecessary**; drop it.
- **Two genuinely NEW `install.sh` actions are required** (today `install.sh` edits only
  `.claude/settings.json:76-85` and `init.sh:88-91` — it touches neither `.claude/commands/`
  nor `CLAUDE.md`):
  1. **Delete `.claude/commands/security-tailor.md`.** TIER1 (`install.sh:62-66`) lists no
     `.claude/commands/` path, so without this the `/security-tailor` command survives and
     dangles at a deleted `Security-kit/`. Add the path to `TIER1=(...)`.
  2. **Strip the `CLAUDE.md` `@import` + the command references.** `install.sh` has zero
     `CLAUDE.md` edits today; the manifest *says* CLAUDE.md is hand-neutralized
     (`SECURITY-MANIFEST.md:57,79`) but no code does it. Add a `sed`/python step (mirror of
     the `init.sh` strip at `install.sh:88`) to remove: the `@Security-kit/active-controls.md`
     line, the `/init-project` Step 2b, and the `/session-cycle` sign-off step. This edit
     *also* finally implements the manifest's currently-unbacked CLAUDE.md neutralization.
- **`SECURITY-MANIFEST.md`** — add to Tier 1: `.claude/commands/security-tailor.md`,
  `kiro/steering/security-tailor.md`, `kiro/steering/active-controls.md` (the only *new*
  paths not already covered by a dir entry). Add to Tier 3 row for `CLAUDE.md`: the
  `@Security-kit/active-controls.md` import + Step 2b + sign-off references.

### 5.3 What you observe (the A/B contrast)
| Scenario | Full build | `--no-security` build |
|---|---|---|
| Product adds a data flow, control never mapped | `check_coverage.py` fails → `init.sh` **cannot go green** | no coverage gate → `init.sh` **passes silently** |
| `coverage.json` | present, fresh, gates | absent |
| Security reasoning | ran at init + every sign-off | never ran |
| Agent's session context (layer D) | tailored `active-controls.md` in context — attends to THIS product's controls while coding | no tailored steering; only generic `SECURITY.md` (if kept) or nothing |
| Product code scanned for selected sinks | `sast_scan.py` runs in block 5b; findings surfaced | never scanned |

This adds a **sharper failure mode** to the template's existing A/B story (full build
24/24 vs no-security 16/24, per `SECURITY-MANIFEST.md:84`): "you extended the attack surface
without extending control coverage" now shows as a red board.

### 5.4 "Missed it in init" is not silent
If `/init-project` skips Step 2b → `coverage.json` never generated → `check_coverage.py`
fails on rule 1 (missing) → `init.sh` **FAIL**, naming the missing artifact. Fix = run
`/security-tailor` once (T2). The `--no-security` build is the only place the check is
stripped, so a deliberately ungoverned project isn't nagged for a file it removed —
covered for free by the `if [ -d "governance" ]` guard.

---

## 6. Evaluation — how we know it works

Effectiveness has **two distinct questions**, and each is measured with the SAST
benchmark idiom — a **labeled corpus + confusion matrix**, exactly how OWASP Benchmark
scores a static analyzer (score cases labeled true/false per weakness → TP/FP/TN/FN →
recall & precision). No hand-waving anecdotes; a tracked number.

- **Q1 — is the *selection* correct?** (does the tailor pick the right controls for a
  described product) → §6.2.
- **Q2 — does the *product code* contain the sinks?** (does `sast_scan.py` catch planted
  vulnerabilities) → §6.3.

### 6.1 Plumbing (mechanical, CI-able — necessary, not sufficient)
- `tests/test_coverage.py` (§4.4) — the checker's ground truth, wired into `init.sh`
  **block 5b** (the security-integrity block, `init.sh:112-181`), not block 4 (block 4
  runs only `test_fixtures.py` by name, `init.sh:77`).
- `init.sh` on a fresh full copy: **FAILs** citing missing `coverage.json`; after
  `/security-tailor` + filled verifications: **PASS**. (Gate has teeth.)
- **Wiring/consistency asserts:** `check_coverage.py` asserts `active-controls.md` exists
  and its control set == `coverage.json` `applies` set; a test asserts `CLAUDE.md` contains
  the `@import` (else layer D is inert — same failure class block 5b already guards for
  `permission.py`, `init.sh:122`).

These prove the machine *runs*. They do **not** prove it is *right* — that is §6.2/§6.3.

### 6.2 Q1 — Selection benchmark (confusion matrix on the tailor)
Treat **`applies` = the positive/"vulnerable" class.** Build a small labeled corpus and
score the tailor's verdicts against ground truth.

- **Corpus:** `Security-kit/eval/corpus/` — 3–5 synthetic product descriptions (a
  `context/`-shaped folder each), every one of the 20 OWASP ids **hand-labeled**
  `applies` / `n_a` by a human. ≈ 60–100 labeled cells. `claims-agent/context/` is **one
  row** of this corpus, not the whole eval.
- **Score:** run the tailor headless → compare verdict vs label → confusion matrix:

  | | truly applies | truly n_a |
  |---|---|---|
  | predicted applies | TP | FP (over-select — cheap: an extra matrix row) |
  | predicted n_a | **FN — MISSED CONTROL** | TN |

- **Headline = recall = TP/(TP+FN).** A false `n_a` is a **false negative = a missed
  vulnerability class**, the SAST failure that matters. Target recall → 1.0; precision is
  secondary (guards alert fatigue). This *replaces* rev 2's anecdotal "false-N/A audit"
  with a measured, regression-trackable number.
- **Runner:** `Security-kit/eval/eval_selection.py` prints the matrix + recall/precision;
  a regression test fails if recall drops below a set floor on the frozen corpus.
- **Idempotence:** re-running on unchanged corpus yields identical `coverage.json` (stable
  hash + verdicts) — a corpus row doubles as the idempotence check.

### 6.3 Q2 — Scanner benchmark (detection rate on planted vulns)
`sast_scan.py` (§4.6) is itself scored like a SAST tool against **planted-vulnerability
code**, so its heuristic limits are quantified, not claimed away.

- **Corpus:** `Security-kit/eval/vuln-corpus/` — small code samples, each **labeled** with
  the sink it does/doesn't contain: e.g. a tool with `subprocess(…, shell=True)` (LLM06),
  a hardcoded API key (LLM02), a wildcard `mcp-allowlist.json` scope (ASI04), an
  unvalidated URL builder (SSRF) — paired with clean look-alikes (for FP measurement).
- **Score:** run `sast_scan.py` → confusion matrix over sinks → **detection rate =
  recall on planted vulns**, plus FP rate on the clean look-alikes. Report both; a strict
  mode can require recall ≥ floor.
- **Real-world anchor:** `claims-agent` has **no product `.py` to scan** (its `tools/` is
  `ARCHITECTURE.md` + `mcp-allowlist.json` only — verified 2026-08-04). The one live check
  it exercises is **wildcard tool scope in `tools/mcp-allowlist.json`** (ASI04). So the
  planted-vuln corpus is the scanner's primary proving ground; claims-agent is the "does
  it run on a real project" smoke test, honestly labeled as such.
- **Binding to Q1:** the scanner only checks controls the tailor marked `applies` — so a
  tailor false-negative (§6.2) *cascades* into "sinks never scanned." This is why the two
  benchmarks are reported together, and why the tailor's recall is the upstream headline.

### 6.4 A/B differential (the template's own evaluation idiom)
Full build vs `install.sh --no-security` on the same product-with-a-new-dataflow: full
fails the coverage gate + runs the scan; no-security does neither and passes. Record in
the style of `examples/claims-agent/evaluation/TEMPLATE-EVALUATION-REPORT.md`.

### 6.5 Success criteria
1. Fresh full build cannot reach `init.sh` PASS without a coverage pass.
2. `/security-tailor` runs standalone from just `Context/`.
3. `--no-security` cleanly strips all new pieces (incl. `.claude/commands/security-tailor.md`,
   `active-controls.md` + its `CLAUDE.md` import); that build still passes its own
   (reduced) `init.sh` with **no dangling command or import** (the audit fix, §5.2).
4. Every verdict in `coverage.json` carries a `Context/` citation.
5. Zero new runtime dependencies (stdlib python + bash only) — including `sast_scan.py`
   (stdlib `ast` + regex, per §4.6).
6. **Layer D live:** tailored `active-controls.md` present, loaded by `CLAUDE.md`, lists
   exactly the `applies` controls.
7. **Q1 selection recall** measured on the frozen corpus and ≥ floor (headline metric).
8. **Q2 scanner detection rate** measured on the planted-vuln corpus and ≥ floor.

---

## 7. Advice / recommendation

1. **Build order: tailor first, scanner second, both benchmarked.** The tailor (§4.1–4.5)
   + its selection benchmark (§6.2) is the load-bearing half — ship and trust it first.
   `sast_scan.py` (§4.6) + its planted-vuln benchmark (§6.3) is the second half and depends
   on `coverage.json` existing. Still deferred beyond this spec: policy-diff generation and
   *inventing* controls (original Approach C) — out of scope here.
   **On SAST honesty:** the tailor is design-time **threat modeling / control selection**,
   NOT SAST; `sast_scan.py` IS SAST-the-capability but **heuristic** (stdlib AST+regex, no
   interprocedural taint — §4.6). Never label it "SAST-complete." The §6.3 detection-rate
   number is the honest statement of what it catches. The *methodology* (labeled corpus +
   confusion matrix) is borrowed from SAST for BOTH halves; the *capability* is SAST only
   for the code scan.
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
7. **Layer D is advisory by nature — wire it, don't overclaim it.** A steering file shapes
   the agent's behavior; it does not *force* it. The mechanical backstop stays
   `permission.py` (blocks) + `check_coverage.py` (gates completeness). So the honest claim
   is: "the agent is *prompted with* this product's controls while coding," not "the agent
   *cannot violate* them." What we DO make mechanical about layer D is that it exists, is
   loaded (CLAUDE.md import), and matches the selection (§6.1) — an unwired or stale
   steering file fails `init.sh`. That converts "did we remember to steer?" from hope into
   a checked fact, which is the most that's honestly enforceable for advisory guidance.

---

## 7b. Implementation phasing (decided 2026-08-04)

Build in two phases; **Phase 1 (tailor + selection benchmark) ships and is trusted before
Phase 2 begins.** Each phase leaves `init.sh` green on its own.

| Phase | Delivers | Pieces | Eval | Done when |
|---|---|---|---|---|
| **1 — Tailor (Q1)** | product → selected controls, coverage-gated, dev-time steering, selection recall measured | §4.1 skill, §4.2 coverage.json, §4.3 check_coverage.py, §4.4 test_coverage.py, §4.5 active-controls.md; wiring §5.1/§5.2; §6.2 selection corpus + `eval_selection.py` | §6.2 recall on frozen corpus ≥ floor | fresh full build can't reach PASS without a coverage pass; recall measured & tracked |
| **2 — Scanner (Q2)** | product *code* scanned for the sinks of selected controls, detection rate measured | §4.6 sast_scan.py; §6.3 planted-vuln corpus | §6.3 detection rate ≥ floor | scanner runs in block 5b (warn-default); FN/FP measured on planted corpus |

Phase 2 depends only on Phase 1's `coverage.json` contract, so the boundary is clean —
nothing in Phase 1 is rework. Success criteria §6.5 #7 gates Phase 1; #8 gates Phase 2.

**This plan cycle covers Phase 1 only.** Phase 2 gets its own plan once Phase 1's recall
number is trusted.

---

## 8. Open questions for the engineer
1. **Context hash scope** — hash all of `Context/`, or only the docs the skill actually
   read? (Proposal: all non-template `.md` in `Context/`, sorted, concatenated.)
2. **coverage.json location** — `Security-kit/coverage.json` (proposed) vs alongside the
   matrix. Either works; Security-kit/ keeps security artifacts together.
3. **Granularity** — verdict per OWASP id (20 rows, proposed) vs per SECURITY.md control
   (40 rows). OWASP ids are coarser and map 1:1 to the crosswalk the engineer already
   reviews — recommended for "start small."
