# Selection benchmark (Q1)

Measures whether `/security-tailor` selects the right controls. The scorer
(`eval_selection.py`) is deterministic and unit-tested; the *verdicts it scores* come from
running the (non-deterministic) skill — so recall is an **acceptance measurement, not a CI gate**.

## Corpus
`corpus/<case>/context/*.md` — synthetic product. `corpus/<case>/labels.json` — hand-labeled
truth for all 20 OWASP ids. Positive class = "applies"; `n_a` is negative.

## Producing the recall number (human-run)

> **`/security-tailor` takes no path argument.** It reads `Context/`, named at eight sites in the
> command, and `check_coverage.py:20` hardcodes `CONTEXT_DIR` while `:73`/`:108` build
> `generated_from` from the literal `"Context/ @ …"`. Step 1 below used to say "run it against
> `corpus/<case>/context/`" — corrected 2026-08-15, because that is not a thing the template can do.
> Until a `--context` flag exists (deferred; see build-design §5.1a), the corpus reaches the drafter
> by being copied into `Context/`.

1. Save the template's `Context/` (it holds a README + two `.template` stubs and nothing else),
   then copy one case's `context/product.md` into `Context/`.
2. Run `/security-tailor`.
3. Copy the resulting `coverage.json` to a recorded dir: `recorded/<case>/coverage.json`,
   and the matching `corpus/<case>/labels.json` to `recorded/<case>/labels.json`.
4. **Restore `Context/` and delete `Security-kit/coverage.json`.** Not optional: leaving either in
   place clears two errors that the declared baseline asserts are present, so `./init.sh` must be
   back to `exit 1, 5 error(s)` before the run counts as finished (build-design §7.4.1).
5. Repeat 1–4 per case, then `python3 eval_selection.py recorded/` → TP/FP/FN/TN + recall/precision.

`--stamp` is not part of the measurement: `eval_selection.py:53-56` reads `controls[].verdict` and
the labels, never `generated_from`. Running it adds end-to-end fidelity, not signal.

**Do not read `labels.json` for a case before classifying it.** The labels are the answer key. A run
whose classifier has seen them measures nothing, and the contamination is invisible in the output —
the recall figure looks the same either way. If it happens, record the case as contaminated and
re-run it in a fresh session rather than reporting the number.

**Headline = recall.** A false `n_a` (predicting n_a when the label is applies) is a false
negative = a missed control. Target recall → 1.0; track regressions across skill revisions.
The `recorded/` dir is git-ignored (it is a measurement snapshot, not source).

## Measured runs

| Date | Cases | TP | FP | FN | TN | recall | precision |
|---|---|---|---|---|---|---|---|
| 2026-08-15 | 2 (`claims-agent`, `multi-agent-product`) | 33 | 0 | 2 | 5 | 0.943 | 1.000 |

`rag-product` excluded as **contaminated** — its labels were read before classifying.
Both FNs are in `claims-agent` and share one cause: `n_a` asserted from a structural absence that
does not remove the property the id names (ASI03 = privilege, not cloud IAM; ASI08 = a sequence
property, not a topology one). Full write-up and the proposed one-line fix to `security-tailor.md`:
build-design §5.1a task 5.

Read precision with care: `n_a` was predicted 7 times in 40, so there was little chance to be wrong
in the negative direction. 9 of 35 positive predictions were `gap`, and all 9 were correct — the
"never guess ⇒ gap" rule is doing the work.
