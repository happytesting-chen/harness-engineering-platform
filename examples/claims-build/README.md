# Example — Claims Agent (built with the harness)

A deterministic insurance-claims triage agent, **built inside this harness from an empty
copy of `template/`**. This is the most complete worked example in the repo: three phases
signed off by a human, a fourth open, and a measured evaluation snapshot.

Read it for two different things:

1. **What a filled harness looks like** — no `{{placeholders}}`, real phase verifications,
   real policy, a `progress.md` with 4 sessions of decisions.
2. **Where the product code went** — the layout question `template/README.md` Step 6b
   answers is answered *concretely* here.

> **Not the template.** If you want to start a project, copy
> [`../../template/`](../../template/), not this directory. This one is already filled for a
> claims domain, and it is on an **older template generation** — see
> [What this example predates](#what-this-example-predates) at the bottom, which matters if
> you diff the two.

---

## Run it

```bash
./init.sh
python3 -m pytest tests claims/tests extraction/tests -q
```

Measured 2026-08-17 on this tree:

| Command | Result |
|---|---|
| `./init.sh` | **exit 0** — `RESULT: PASS with 1 warning(s)` |
| `pytest tests claims/tests extraction/tests -q` | **50 passed** in 0.38s |

The one warning is `progress.md is older than recent code changes`. It is expected in a
fresh clone and not a defect: git does not preserve mtimes, so the freshness check compares
timestamps that a checkout has flattened.

No API key, no `pip install` — Python 3.11+ and bash.

---

## What the agent does

From `CLAUDE.md`: *"a minimal, deterministic Python claims-processing workflow evaluated
locally on committed synthetic data only. It has no production claims role."*

Every reviewed case flows **validate → normalize → deterministic route → exactly one
minimal local result**, with terminal outcomes `APPROVED`, `REJECTED`, or
`PENDING_REVIEW`. **There is no permissive fallback** — an input that matches no rule
becomes `PENDING_REVIEW`, never an approval.

Two design choices are worth stealing:

- **One decision authority.** `claims/router.py` is documented as *"Stage 3 — Route (sole
  decision authority)"*: fixed-order rules, no fallback. Nothing else in the pipeline may
  decide an outcome, so there is exactly one file to review for "can this approve something
  it shouldn't?".
- **The extractor is not trusted with money.** Phase 04 adds an LLM front-end that reads
  claim prose. `extraction/service.py` **overrides** `covered_amount` and `currency` from a
  trusted policy store after extraction, so a plausibly-lying extractor cannot fabricate an
  approval. The model contributes fields; it does not contribute authority.

---

## Layout — harness vs product

```
claims-build/
├── CLAUDE.md · Harness-Best-Practice/ · governance/ · Security-kit/   ← harness
├── tests/                  ← harness proofs (fixtures, e2e, hooks, content-trust)
├── claims/                 ← PRODUCT — 451 lines
│   ├── validate.py · normalize.py · router.py · pipeline.py
│   ├── outcomes.py · runner.py · writer.py
│   └── tests/              ← product proofs, next to the code
│       ├── test_determinism.py · test_fixtures_flow.py
│       ├── test_runner.py · test_writer_fail_closed.py
│       └── fixtures/
├── extraction/             ← PRODUCT (phase 04) — 194 lines
│   ├── model.py · policy_store.py · service.py
│   └── tests/test_extraction.py
├── demo/ · evaluation/     ← the "it matters" and "it's good" proofs
└── progress.md · findings.md · task_plan.md
```

Product tests live **inside the product packages**, never in the top-level `tests/`. That
is deliberate: `tests/` belongs to the harness and `install.sh --no-security` deletes it
wholesale along with `governance/` and `Security-kit/`.

---

## The phases (and the sign-offs)

`Harness-Best-Practice/feature_list.json` — project *"Claims Agent — Core Harness
Evaluation"*:

| Phase | Name | Status | Verification |
|---|---|---|---|
| `phase-01` | Build A readiness review | **passing** | `./init.sh` + assert `claims/` is still empty |
| `phase-02` | Deterministic Build A implementation | **passing** | `./init.sh && python3 -m pytest tests claims/tests -v` |
| `phase-03` | Build A evaluation and snapshot | **passing** | same as 02 |
| `phase-04` | Build C — LLM extraction front-end | **active** | `./init.sh && pytest tests claims/tests extraction/tests -v && python3 evaluation/eval.py --snapshot evaluation/build-c` |

Two details that show the mechanism working rather than being described:

- **Phase 01 verifies an absence.** Its command asserts `claims/` contains no files — a
  readiness gate that *cannot* be satisfied by writing code early. The harness's rule that
  a phase is defined by an observable outcome does not require that outcome to be a feature.
- **Every `passing` was set by a human, and the evidence says who and when.** Phase 02's
  evidence field records `2026-08-04: ./init.sh clean PASS (exit 0) && … => 38 passed …
  Human sign-off recorded`. Phase 04's records the gating prerequisite that had to clear
  before any extractor code was allowed to exist. The agent wrote the code; it did not
  promote itself.

---

## The evaluation snapshot

`evaluation/build-a/SNAPSHOT.md`, generated by `python3 evaluation/eval.py --snapshot
evaluation/build-a`. Target: `claims.decide` over `claims/tests/fixtures/*.json`.

| Axis | Value |
|---|---|
| Cases | 5, repeated 3× each |
| Accuracy | 100.0% (5/5) vs oracle |
| Reproducibility | 100.0% (5/5) identical across repeats |
| Latency | mean 0.008 ms · max 0.024 ms |
| Cost | `N/A (no real provider wired)` |

Note what it does **not** claim. 5 cases is a smoke-level oracle, not a benchmark, and cost
prints `N/A` instead of a fabricated number because no provider is wired — the honest-absence
convention the harness enforces everywhere. 100% accuracy here means *the deterministic
engine agrees with its own oracle on five fixtures*; it is a regression baseline, not
evidence the product is good.

---

## What this example predates

Stated so a diff against `template/` does not read as "the example is broken". Measured
2026-08-17:

| Present in `template/` | In this example |
|---|---|
| 11 harness suites in `tests/` | 4 (`test_fixtures`, `test_e2e`, `test_hooks`, `test_content_trust`) |
| The coverage gate (`Security-kit/check_coverage.py`, wired into `init.sh`) | absent — `grep -c check_coverage init.sh` = 0 |
| `/security-tailor` and 4 slash commands | 3 commands; no `security-tailor.md` |
| `Security-kit/coverage.json` · `mechanisms.json` · `requirements.json` | none — the claims-register and requirement-spine planes came later |
| Invariants I1–I6 in the health check | not run here |

So this example's `./init.sh` exits **0**, while a fresh `template/` copy exits **1** with 5
errors until you fill it and run `/security-tailor`. Both are correct for their generation.
Porting this build onto the current template is tracked work, not a claim made here.

---

## Related

- [`../../template/README.md`](../../template/README.md) — the manual: 10 steps from empty
  copy to a signed-off phase
- [`../../docs/evaluations/2026-08-template-ab/TEMPLATE-EVALUATION-REPORT.md`](../../docs/evaluations/2026-08-template-ab/TEMPLATE-EVALUATION-REPORT.md)
  — the A/B write-up that used this build to test *the template itself*
- `progress.md` · `findings.md` — the session journal and decision record for this build
