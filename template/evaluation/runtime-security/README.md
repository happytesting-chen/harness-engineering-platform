# Runtime security — the measured record

Everything in this directory is evidence for one profile (`runtime-mvp`) at one pinned
revision. Nothing here is a claim without a command that reproduces it.

## Read in this order

| File | What it is | Start here if you are… |
|---|---|---|
| [`VERDICT.md`](VERDICT.md) | The signed release decision — `DEPLOY_WITH_RULES`, five conditions, fixed expiry, scoped to the exact revision, policy digest and classifier lock | deciding whether to deploy |
| [`limitations.md`](limitations.md) | Every disabled or untested capability, and the three residuals (R-1 classifier authority, R-2 review queue, R-3 deployed-profile only) | assessing risk |
| [`verification-summary.md`](verification-summary.md) | Each claim → the test that proves it, plus the reviewer checklist | doing the independent review (condition C-4) |
| [`classifier-selection.md`](classifier-selection.md) | Why this classifier, measured: 14/16 attacks, 3/8 legitimate withheld, the two accepted misses with confidences | questioning detection quality |

## Raw evidence

| File | Produced by | Reproduce |
|---|---|---|
| `attack-traces.jsonl` | 13 attack classes driven through the real host | `python3 Security-kit/runtime/attack_driver.py --output /tmp/t.jsonl` — byte-identical on re-run |
| `replay-results.json` | Verdicts re-derived from stored traces alone, no model in the loop | `python3 -m pytest tests/runtime/test_replay.py -q` |
| `classifier-candidates/*.result.json` | Immutable benchmark output per candidate | `python3 Security-kit/eval/eval_runtime_injection.py --candidate-manifest …` |
| `candidate-manifests/*.json` | The exact artifacts each benchmark measured | — |
| `requirements.lock.txt` | The pinned venv for the classifier process (the one non-stdlib dependency) | — |
| *(not here)* the classifier | 700 MB, deliberately not shipped; the lock's paths are operator-local | `python3 Security-kit/eval/bootstrap_classifier.py bootstrap` rebuilds it from `Security-kit/eval/classifier-source.json`, verified by digest, then re-runs this benchmark and compares every case |

## Two rules that govern all of it

**Score on damage, not self-report.** A case is RESISTANT only when the observable side
effect did not happen — the spy tool recorded zero calls, the transport carried no secret.
No case passes because a component said it blocked something.

**The verdict expires.** Every number was measured against one tree. Change the policy, the
classifier lock or `Security-kit/runtime/` and the verdict lapses — into nothing, not into a
stronger claim. Re-signature requires re-running the evidence.

## Rendered pages

[`pages/four-gates.html`](pages/four-gates.html) (the capability brief) and
[`pages/evidence-ledger.html`](pages/evidence-ledger.html) (the measured record, explained)
are self-contained HTML renderings of this directory for an external reader. **This
directory is their source of truth.** Every figure on them was taken from the files above
at one revision; when a number here moves, the page is stale until it is re-checked. They
sit in their own subfolder so rendered views are never mistaken for evidence.
