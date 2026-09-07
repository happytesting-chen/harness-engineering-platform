# Claims and evidence: how you know any of this is true

Two layers answer that question, and they fail differently. The **claims plane** is design-time
truth: every documented control names its mechanism and its proof, and six invariants refuse to
let a claim outrun its code. The **evidence** is measured truth: the tests, traces and benchmark
results on one revision, and the signed verdict that rests on them.

## The tailoring path (build-time, human-reviewed)

The two paths meet at a **file**, not at a function call. The model writes it once; the
mechanism reads it thereafter.

```
  Context/*.md          /security-tailor          coverage.json        check_coverage.py
  ────────────          ────────────────          ─────────────        ─────────────────
  product design   ──►  a MODEL reads and    ──►  which controls  ──►  every "applies"
  AI stack              classifies                apply to THIS         control maps to a
  deployment target     (proposes only)           product              control-matrix.md
  scope                        │                                       row with a real
                               │                                       Verification
                               ▼                                              │
                    active-controls.md                                        ▼
                    loaded EVERY session                                  ./init.sh
                    via CLAUDE.md                                     exit ≠ 0 → blocked
                               │
                               ▼
                    ┌─────────────────────────────────────────────┐
                    │  A model may only decide things a human     │
                    │  reviews BEFORE they take effect.           │
                    └─────────────────────────────────────────────┘
```

The gate enforces **completeness** (a verification is mapped), not **adequacy** (that it
is a good check). Adequacy stays with human review and sign-off.

## What is actually mechanical — and what is not

Honest status, as of this commit. "Mechanical" means an execution path enforces it **and**
a test proves that path.

| Layer | Where | Status |
|---|---|---|
| Control plane, dev-time | `governance/permission.py` via PreToolUse | **Mechanical.** Wired in `.claude/settings.json`, proven by `tests/test_hooks.py`, gated in `init.sh` block 5b |
| Self-protection (S2.4) | `check_protected_paths` (Gate ①a) | **Mechanical.** Blocks writes to the mechanism and policy by *file identity* — traversal, absolute, symlink, hard-link and case-variant forms all collapse to the same target (`os.path.samefile`, so identity not spelling). Additive-only policy: `BUILTIN_PROTECTED_PATHS` holds even if the policy key is emptied or deleted. Proven by `tests/test_protected_paths.py`. **One open vector of those tested:** an interpreter one-liner (`python3 -c open(...,'w')`), documented in `SECURITY.md` S2.4 and pinned by a test so it cannot close silently without the doc changing |
| Credential block, dev-time | `Security-kit/secret_scan.py` | **Mechanical.** Wired in `.claude/settings.json` |
| Coverage completeness | `check_coverage.py` inside `./init.sh` | **Mechanical, and currently failing closed** — no `coverage.json` on disk yet, so it exits 1 until `/security-tailor` runs |
| Audit trail | `Harness-Best-Practice/observability/audit_hook.py` | **Mechanical** for observation only — PostToolUse cannot veto |
| Data plane, `scan_text` | `Security-kit/content_trust.py` | **Mechanical via two adapters.** `prompt_screen.py` (①) and `result_screen.py` (④) both call it and both *act* on the report — erase the prompt, replace the output. Neither adapter owns a pattern; `_INJECTION_MARKERS` lives here alone, and anti-drift tests scan adapter source to keep it that way |
| Data plane, `screen_record` | `Security-kit/content_trust.py` | **Library only.** Field allowlisting for structured records is tested and has no caller — no ingestion path uses it |
| Tool coverage | the `matcher` in `.claude/settings.json` | **Gap.** It lists five tools; anything outside it (`WebFetch`, MCP writes, subagent spawns, scheduled jobs) reaches no gate. Gate ①a *would* judge an MCP write carrying a `path`, but the matcher never invokes it |
| Prompt-entry gate (①) | `Security-kit/prompt_screen.py` via UserPromptSubmit | **Mechanical.** Wired in `.claude/settings.json`, exit 2 erases the prompt, proven by `tests/test_prompt_screen.py`. It is a protected path. **Enforcement is exact; detection is not** — fires once per human turn only, and a paraphrase outside the markers passes |
| Result screen (④) | `Security-kit/result_screen.py` via PostToolUse | **Mechanical.** Replaces the tool output via `updatedToolOutput` before the model reads it, shape-preserving so the runtime cannot discard the substitution. Fires per tool call, matcher `*`. Proven by `tests/test_result_screen.py`. It does **not** undo the call — ③ has already happened |
| Runtime enforcement (deployed app) | `governance/runtime_dispatcher.py`, `Security-kit/runtime_screen.py` (regex tier); `Security-kit/runtime/` — 16 modules, semantic tier, 146 tests | **Mechanical when called, and calling it is opt-in.** All four gate positions exist in process, importing the *same* `permission.py` and the same policy JSON as the hooks; proven by `tests/test_runtime_dispatcher.py` and `tests/test_runtime_screen.py`. **The residual is the wiring:** nothing checks that your application routed through them (`SEC-RUNTIME-GAP-001`, SECURITY.md S1.6) |

Two boundaries worth stating plainly:

- **`demo/` is not the production path.** It is scripted evaluation infrastructure
  (`demo/ARCHITECTURE.md:3`). The real path is `.claude/settings.json` hooks →
  `governance/permission.py` CLI mode (`demo/ARCHITECTURE.md:29`).
- **Dev-time ≠ runtime, and both now ship.** A dev-time hook is a *subscription to Claude
  Code's event loop* — JSON on stdin, exit 2 to block. A deployed agent (LangChain,
  Strands, a plain loop) has no hook system; there, enforcement is a function your app
  calls. The kit ships both: `governance/runtime_dispatcher.py` for ② ③ ④ and
  `Security-kit/runtime_screen.py` for ① ④, over the same policy files. What is *not*
  mechanical is the call site — a copy of this harness inherits the design and none of the
  enforcement until the application routes through those two modules.

## The claims register and its six invariants

The table above is a claim. `Security-kit/mechanisms.json` is the same information
in a form a program can check, and `check_coverage.py` checks it on every
`./init.sh`:

| File | Plane | Owner |
|---|---|---|
| `control-matrix.md` | what the kit CLAIMS, in prose a human reviews | human |
| `mechanisms.json` | what each mechanism IS — `decides`, `attaches_at`, `can_deny`, `proof` | human, at merge time |
| `requirements.json` | what the project is OBLIGED to guarantee, with residuals | human, at merge time |

Six invariants join them. Each prints its **skip count** and the **population it
walked**, because a check that silently skipped everything and a check that passed
everything otherwise produce the same output:

| Invariant | Asserts | Notable limit |
|---|---|---|
| **I1** | the register and the matrix agree, keyed on the implementation path **and the function on the same line** | a matrix row naming only a file cannot join, and skips — counted, not hidden |
| **I2** | each row is internally coherent, and `status` equals the value **derived** from `(decides, attaches_at, can_deny)` | a pure function of one row: it can never skip |
| **I3** | each `proof` names one file that exists **and** that `init.sh` selects | reachability is a property of the build; specificity is a property of the claim |
| **I4** | no orphans in either direction; an **unlabelled** matrix row is an error | `SEC-TAILOR-Z3` is exempt: a prompt in the register would claim power it lacks |
| **I5** | every Zone-3 drafter states its five guardrails | text **presence** only — it cannot check that a drafter obeys them |
| **I6** | every requirement names a real control; every non-`GAP` row is asked for by a requirement | a `GAP` row may serve a requirement, but only if that requirement states a `residual` |

**I6 fails closed, and fails closed without going quiet.** An unreadable or missing
`requirements.json` is an error, not an absence of obligations — but the error is
added as a *sixth row of the report*, never as an early return. The distinction is
the whole point: an early return fires before the print loop and would replace all
six lines with one, so a single unreadable spine would leave I1–I5 unreported at
exactly the moment you most need to know they still pass. On that branch the printed
line reads `0/22 matrix rows checked, skipped 22`, which is the honest description of
a walk that never happened.

The spine was drafted by a model and installed by a human, because
`requirements.json` is human-owned at merge time — a model-written claims register is
the inversion the plane split exists to prevent.

Two properties are worth more than the six checks. **`status` is derived, not
chosen**, so the register cannot flatter itself: hand-set a row to `MECHANICAL`
while its `can_deny` is `false` and I2 says so. And **every invariant ships a
mutation** — break the property, watch exactly one invariant redden, revert. An
invariant without a mutation is a claim, not a check.

Neither file is a control. They make the kit's *description* of its controls
mechanically true, which is a smaller thing than enforcement and a different
thing from documentation.

---

The Security Kit is the template's security navigation and review layer. It does not
replace the existing policy, enforcement, or test assets; it connects them to
project-specific controls and review evidence.

## How the evidence is produced and signed

The claims plane says which mechanism backs which claim. The evidence answers a different
question: on the tree as it stands, does the mechanism hold? Everything under
[`template/evaluation/runtime-security/`](../../template/evaluation/runtime-security/) is
produced by a command that anyone can re-run, and the record's own README says which.

| Evidence | What it proves | Produced by |
|---|---|---|
| `attack-traces.jsonl` | Each of the attack cases is RESISTANT on a **side-effect oracle**: the spy tool recorded no call, the transport carried no secret. No case passes because a component said it blocked something. | `python3 Security-kit/runtime/attack_driver.py --output …` — byte-identical on re-run |
| `replay-results.json` | The verdicts can be re-derived from the stored traces with no model in the loop. | `python3 -m pytest tests/runtime/test_replay.py -q` |
| `classifier-candidates/*.result.json` | What the pinned classifier caught and missed on the labelled corpus, per case, at a recorded chunk window. Results are immutable: a new run is a new file. | `python3 Security-kit/eval/eval_runtime_injection.py --candidate-manifest … --output …` |
| `semantic-model.lock.json` (in `Security-kit/runtime/`) | The classifier executable, model and corpus digests a human approved, with the approver and date. | `eval_runtime_injection.py --lock … --verify` re-checks every digest against the tree; startup refuses a lock that does not verify |
| `VERDICT.md` | The release decision, its conditions, and its expiry, signed by a named person. | Written by hand from the evidence above; re-scoped by dated **amendments**, never edited in place |

Two rules govern all of it. **Score on damage, not self-report.** **The verdict expires** on
any change to the source revision, the policy digest, the classifier lock, the corpus, or the
contents of `Security-kit/runtime/`; a change lapses it into nothing, not into a stronger claim.
On another machine, [Bring your own classifier](../guide/03-bring-your-own-classifier.md)
rebuilds the pinned classifier and reproduces the benchmark before a human signs a local lock.
The operator's sequence is [Produce and sign evidence](../guide/05-produce-and-sign-evidence.md).
