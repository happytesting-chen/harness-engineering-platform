# Selection benchmark (Q1)

Measures whether `/security-tailor` selects the right controls. The scorer
(`eval_selection.py`) is deterministic and unit-tested; the *verdicts it scores* come from
running the (non-deterministic) skill — so recall is an **acceptance measurement, not a CI gate**.

## Corpus
`corpus/<case>/context/*.md` — synthetic product. `corpus/<case>/labels.json` — hand-labeled
truth for all 20 OWASP ids. Positive class = "applies"; `n_a` is negative.

## Producing the recall number (human-run)
1. For each case, run `/security-tailor` against `corpus/<case>/context/`.
2. Copy the resulting `coverage.json` to a recorded dir: `recorded/<case>/coverage.json`,
   and the matching `corpus/<case>/labels.json` to `recorded/<case>/labels.json`.
3. `python3 eval_selection.py recorded/` → prints TP/FP/FN/TN + recall/precision.

**Headline = recall.** A false `n_a` (predicting n_a when the label is applies) is a false
negative = a missed control. Target recall → 1.0; track regressions across skill revisions.
The `recorded/` dir is git-ignored (it is a measurement snapshot, not source).
