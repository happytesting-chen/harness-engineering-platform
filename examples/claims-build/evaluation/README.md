# evaluation/

The harness's **third proof**. The first two already exist:

| Dir | Question it answers | Verdict type |
|-----|--------------------|--------------|
| `tests/` | Is the gate **correct**? | pass / fail |
| `demo/` | Does the harness **matter**? | enforced vs `--nogate` |
| **`evaluation/`** | Is the task **good** — accurate, reproducible, cost-effective? | **measured metrics** |

`tests/` and `demo/` assert *yes/no*. `evaluation/` **quantifies** so a human can
judge effectiveness, cost-effectiveness, and accuracy — and sign off a snapshot.

## What it measures

| Axis | Meaning | Real today? |
|------|---------|-------------|
| **Accuracy** | decisions vs a known oracle | ✅ yes |
| **Reproducibility** | identical output across repeat runs | ✅ yes |
| **Latency** | wall-clock per case | ✅ yes |
| **Cost** | tokens / USD | ⚠️ **N/A until a real provider is wired** — never fabricated |

> **Honesty rule.** With the reference wiring (the deterministic `claims.decide`
> engine) there is no real model, so there are no tokens and no dollars. `eval.py`
> prints `N/A (no real provider wired)` rather than inventing a number. Cost becomes
> real only when you pass a `usage_fn` that reports actual provider usage.

## Run it

```bash
python3 evaluation/eval.py                          # measure claims.decide, print report
python3 evaluation/eval.py --snapshot evaluation/build-a   # also write a filled SNAPSHOT.md
```

The reference target is the project's **own** deterministic decision engine,
`claims.decide`, evaluated over the committed labeled fixtures in
`claims/tests/fixtures/*.json` — zero deps, no API key, meaningful number. Exit is
non-zero only if the engine regresses below 100% accuracy or reproducibility.

## Evaluate your real task

`evaluate()` is generic. Supply your own cases, decision function, and oracle key:

```python
from evaluation.eval import evaluate, format_report

cases = [...]                     # each case carries its oracle value
def decide_fn(case): ...          # case -> normalized decision string (under test)
def usage_fn(case):               # OPTIONAL — only if your provider reports usage
    return {"tokens": ..., "usd": ...}

metrics = evaluate(cases, decide_fn, oracle_key="expected", repeats=3,
                   usage_fn=usage_fn)   # omit usage_fn -> cost = N/A
print(format_report(metrics, target="my agent task"))
```

- **`decide_fn`** must be a *pure* read of your task's output for one case — same
  input, same output, no side effects. Reproducibility depends on this.
- **`oracle_key`** points at the expected value already stored in each case (an
  oracle — see below). The oracle is never fed into `decide_fn`.
- **`usage_fn`** is the *only* honest source of cost. No `usage_fn` → cost is N/A.

## The oracle rule

Each case carries its expected answer (its **oracle**). The evaluator compares
`decide_fn(case)` against `case[oracle_key]` — but `decide_fn` must **never read
the oracle**. Keeping the expected value out of the decision path is what makes
the accuracy number mean something. (In this repo, the claims fixtures' `expected`
block is exactly such an oracle: asserted in tests, never passed to `decide()`.)

## Snapshot

`--snapshot DIR` fills `SNAPSHOT.template.md` and writes `DIR/SNAPSHOT.md` — a
human-reviewable record. It is an **evaluation artifact, not a feature**: the agent
does not self-transition phases; a human reviews the metrics and records sign-off
in `Harness-Best-Practice/feature_list.json`.
